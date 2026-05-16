"""Receive and process Evolution API webhook events.

Responsibilities:
  1. Identify the WhatsAppNumber by instance_name
  2. Persist incoming/outgoing messages (deduped by evolution_message_id)
  3. Update connection status when CONNECTION_UPDATE fires
  4. Forward the event to the tenant's configured CRM webhook (sync, Phase 4)

Sync delivery to CRM is intentional for Phase 4 — Phase 5 will introduce an
async queue with retries and HMAC-signed deliveries.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.whatsapp_number import WhatsAppNumber
from app.services.evolution import map_state_to_status
from app.services.webhook_outbound import enqueue_delivery


logger = logging.getLogger(__name__)


# ---- helpers --------------------------------------------------------------
def _normalize_event(raw_event: str) -> str:
    """Evolution sends events like 'messages.upsert' or 'MESSAGES_UPSERT'.
    Normalize to upper snake.
    """
    return raw_event.upper().replace(".", "_")


def _extract_phone(jid: str | None) -> str | None:
    if not jid:
        return None
    return "".join(ch for ch in jid.split("@")[0] if ch.isdigit()) or None


def _extract_content(
    message_payload: dict[str, Any] | None,
) -> tuple[str, str | None, str | None, str | None]:
    """Returns (content_type, text|None, media_url|None, mimetype|None).

    Media URLs are the raw WhatsApp CDN links Baileys puts in the event. They
    require the `mediaKey` plus AES-CBC + HMAC decryption to actually serve the
    bytes — we store them as a hint, but the actual serving happens through
    `GET /messages/{id}/media` which proxies + caches via Evolution.
    """
    if not message_payload:
        return "unknown", None, None, None

    if "conversation" in message_payload:
        return "text", message_payload["conversation"], None, None
    if "extendedTextMessage" in message_payload:
        return "text", message_payload["extendedTextMessage"].get("text"), None, None
    if "imageMessage" in message_payload:
        m = message_payload["imageMessage"]
        return "image", m.get("caption"), m.get("url"), m.get("mimetype")
    if "videoMessage" in message_payload:
        m = message_payload["videoMessage"]
        return "video", m.get("caption"), m.get("url"), m.get("mimetype")
    if "audioMessage" in message_payload:
        m = message_payload["audioMessage"]
        return "audio", None, m.get("url"), m.get("mimetype")
    if "documentMessage" in message_payload:
        m = message_payload["documentMessage"]
        return "document", m.get("fileName"), m.get("url"), m.get("mimetype")
    if "stickerMessage" in message_payload:
        m = message_payload["stickerMessage"]
        return "sticker", None, m.get("url"), m.get("mimetype")
    if "locationMessage" in message_payload:
        return "location", None, None, None
    if "contactMessage" in message_payload or "contactsArrayMessage" in message_payload:
        return "contact", None, None, None
    if "reactionMessage" in message_payload:
        return "reaction", message_payload["reactionMessage"].get("text"), None, None
    return "unknown", None, None, None


def _extract_text_and_type(
    message_payload: dict[str, Any] | None,
) -> tuple[str, str | None]:
    """Backwards-compatible 2-tuple wrapper around _extract_content."""
    ct, text, _, _ = _extract_content(message_payload)
    return ct, text


# Refresh the profile picture at most this often. WhatsApp signs the URLs with
# a short-lived token; this balances freshness vs Evolution load.
PROFILE_PICTURE_TTL = timedelta(hours=6)


async def _fetch_profile_picture_background(
    conversation_id: uuid.UUID,
    instance_name: str,
    remote_jid: str,
) -> None:
    """Fire-and-forget: fetch the contact's profile picture URL via Evolution
    and persist it. Best-effort — failures are swallowed because this is not
    on the critical path of message ingest."""
    from app.db.session import AsyncSessionLocal
    from app.services.evolution import evolution_client

    try:
        url = await evolution_client.fetch_profile_picture_url(
            instance_name, remote_jid
        )
        async with AsyncSessionLocal() as session:
            await session.execute(
                Conversation.__table__.update()
                .where(Conversation.id == conversation_id)
                .values(
                    profile_picture_url=url,
                    profile_picture_fetched_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()
    except Exception as exc:  # noqa: BLE001 — background task, log & swallow
        logger.warning(
            "Could not refresh profile picture for conversation %s: %s",
            conversation_id,
            exc,
        )


async def _get_or_create_conversation(
    db: AsyncSession,
    number: WhatsAppNumber,
    remote_jid: str,
    push_name: str | None,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.whatsapp_number_id == number.id,
            Conversation.remote_jid == remote_jid,
        )
    )
    conv = result.scalar_one_or_none()
    needs_pic_refresh = False
    if conv is None:
        conv = Conversation(
            organization_id=number.organization_id,
            whatsapp_number_id=number.id,
            remote_jid=remote_jid,
            remote_phone=_extract_phone(remote_jid),
            remote_name=push_name,
        )
        db.add(conv)
        await db.flush()
        needs_pic_refresh = True
    else:
        if push_name and conv.remote_name != push_name:
            conv.remote_name = push_name
        last_fetch = conv.profile_picture_fetched_at
        if last_fetch is None or (
            datetime.now(timezone.utc) - last_fetch >= PROFILE_PICTURE_TTL
        ):
            needs_pic_refresh = True

    if needs_pic_refresh:
        asyncio.create_task(
            _fetch_profile_picture_background(
                conv.id, number.instance_name, remote_jid
            )
        )

    return conv


# ---- public handler -------------------------------------------------------
async def handle_evolution_event(
    db: AsyncSession,
    number: WhatsAppNumber,
    payload: dict[str, Any],
    arq_pool=None,
) -> dict[str, Any]:
    """Main dispatcher. Persists data, then enqueues an async CRM delivery.

    arq_pool may be None in tests; when so, we skip enqueue and surface that.
    """
    event = _normalize_event(payload.get("event", ""))
    data = payload.get("data") or {}

    # Capture webhook config eagerly — DB ops below could expire the object on
    # rollback paths, breaking attribute access in async context.
    webhook_active = number.webhook_active
    webhook_url = number.webhook_url
    webhook_secret = number.webhook_secret
    webhook_events = list(number.webhook_events or [])
    webhook_format = number.webhook_format
    webhook_extra = dict(number.webhook_extra or {})
    our_phone_number = number.phone_number
    instance_name = number.instance_name
    organization_id = number.organization_id
    number_id = number.id

    summary: dict[str, Any] = {"event": event, "instance": instance_name}

    if event in ("MESSAGES_UPSERT", "SEND_MESSAGE"):
        summary["message"] = await _handle_message_upsert(db, number, data, payload)
    elif event == "MESSAGES_UPDATE":
        summary["update"] = await _handle_message_update(db, number, data)
    elif event in ("CONNECTION_UPDATE", "CONNECTION_STATE"):
        summary["connection"] = await _handle_connection_update(db, number, data)
    # QRCODE_UPDATED: we poll directly, ignore here.

    # Enqueue async CRM delivery (Phase 5 — durable, retried).
    if webhook_active and webhook_url and webhook_secret:
        if webhook_format == "external_neotel":
            await _dispatch_external_neotel(
                db=db,
                arq_pool=arq_pool,
                organization_id=organization_id,
                number_id=number_id,
                instance_name=instance_name,
                event=event,
                payload=payload,
                webhook_url=webhook_url,
                webhook_secret=webhook_secret,
                webhook_extra=webhook_extra,
                upsert_result=summary.get("message"),
            )
            return summary

        if webhook_format == "apiwha_neotel":
            await _dispatch_apiwha(
                db=db,
                arq_pool=arq_pool,
                organization_id=organization_id,
                number_id=number_id,
                instance_name=instance_name,
                event=event,
                payload=payload,
                webhook_url=webhook_url,
                webhook_secret=webhook_secret,
                our_phone_number=our_phone_number,
                upsert_result=summary.get("message"),
            )
            return summary

        if webhook_format == "neotel_custom":
            key = (data.get("key") or {}) if isinstance(data, dict) else {}
            should_deliver = (
                (event == "MESSAGES_UPSERT" and not bool(key.get("fromMe")))
                or event == "MESSAGES_UPDATE"
            )
            if should_deliver:
                await _dispatch_neotel_custom(
                    db=db,
                    arq_pool=arq_pool,
                    organization_id=organization_id,
                    number_id=number_id,
                    instance_name=instance_name,
                    event=event,
                    payload=payload,
                    webhook_url=webhook_url,
                    webhook_secret=webhook_secret,
                    webhook_extra=webhook_extra,
                    our_phone_number=our_phone_number,
                    upsert_result=summary.get("message"),
                )
            return summary

        # Portal format (default): the user-configurable event filter applies.
        should_deliver = not webhook_events or event in [
            e.upper() for e in webhook_events
        ]
        if should_deliver:
            delivery = await enqueue_delivery(
                db,
                arq_pool,
                organization_id=organization_id,
                whatsapp_number_id=number_id,
                target_url=webhook_url,
                secret=webhook_secret,
                event_type=event,
                instance_name=instance_name,
                raw_event_payload=payload,
                format=webhook_format,
            )
            summary["crm_delivery_id"] = str(delivery.id)
            summary["crm_delivery_status"] = delivery.status

    return summary


async def _dispatch_external_neotel(
    *,
    db: AsyncSession,
    arq_pool,
    organization_id,
    number_id,
    instance_name: str,
    event: str,
    payload: dict[str, Any],
    webhook_url: str,
    webhook_secret: str,
    webhook_extra: dict[str, Any],
    upsert_result: dict[str, Any] | None,
) -> None:
    """Build the Neotel ExternalApplication Message Entity and enqueue with
    ApplicationId + AccessToken headers.

    Only inbound MESSAGES_UPSERT (not fromMe) is forwarded — status updates
    and outbound echoes don't have an obvious mapping in the ExternalApp
    Message Entity. They can be wired later if Neotel ends up needing them.
    """
    from app.services.webhook_outbound import (
        build_external_neotel_payload,
        enqueue_delivery,
    )

    if event != "MESSAGES_UPSERT":
        return
    key = (payload.get("data") or {}).get("key") or {}
    if bool(key.get("fromMe")):
        return
    if not upsert_result:
        logger.warning(
            "external_neotel delivery skipped: no message context for %s",
            number_id,
        )
        return

    application_id = (webhook_extra.get("application_id") or "").strip()
    access_token = (webhook_extra.get("access_token") or "").strip()
    if not application_id or not access_token:
        logger.warning(
            "external_neotel delivery skipped: number %s is missing application_id or access_token",
            number_id,
        )
        return

    prebuilt = build_external_neotel_payload(
        raw_event=payload,
        application_id=application_id,
        remote_phone=upsert_result.get("remote_phone"),
        remote_name=upsert_result.get("remote_name"),
        content_type=upsert_result.get("type"),
        message_uuid=upsert_result.get("persisted_message_id"),
    )

    delivery = await enqueue_delivery(
        db,
        arq_pool,
        organization_id=organization_id,
        whatsapp_number_id=number_id,
        target_url=webhook_url,
        secret=webhook_secret,
        event_type=event,
        instance_name=instance_name,
        raw_event_payload=payload,
        format="external_neotel",
        prebuilt_payload=prebuilt,
        extra_headers={
            "ApplicationId": application_id,
            "AccessToken": access_token,
        },
    )
    logger.info(
        "external_neotel delivery enqueued: %s for event %s",
        delivery.id,
        event,
    )


async def _dispatch_apiwha(
    *,
    db: AsyncSession,
    arq_pool,
    organization_id,
    number_id,
    instance_name: str,
    event: str,
    payload: dict[str, Any],
    webhook_url: str,
    webhook_secret: str,
    our_phone_number: str | None,
    upsert_result: dict[str, Any] | None,
) -> None:
    """Build rapiwha-compatible INBOX / MESSAGEPROCESSED / MESSAGEFAILED event
    and enqueue. Body is wrapped as `data=<json>` at dispatch time.

    Event mapping (Evolution → rapiwha):
      - MESSAGES_UPSERT inbound (not fromMe)     → INBOX
      - SEND_MESSAGE                              → MESSAGEPROCESSED
      - MESSAGES_UPDATE with error/failed status  → MESSAGEFAILED
      - everything else                           → skipped
    """
    from app.services.webhook_outbound import (
        build_apiwha_failed_event,
        build_apiwha_inbox_event,
        build_apiwha_processed_event,
        enqueue_delivery,
    )

    key = (payload.get("data") or {}).get("key") or {}
    from_me = bool(key.get("fromMe"))

    if event == "MESSAGES_UPSERT" and not from_me:
        prebuilt = build_apiwha_inbox_event(
            our_phone_number=our_phone_number,
            raw_event=payload,
            remote_name=(upsert_result or {}).get("remote_name"),
        )
    elif event == "SEND_MESSAGE":
        prebuilt = build_apiwha_processed_event(
            our_phone_number=our_phone_number,
            raw_event=payload,
        )
    elif event == "MESSAGES_UPDATE":
        status_value = ((payload.get("data") or {}).get("status") or "").upper()
        if status_value in ("ERROR", "FAILED", "FAIL"):
            prebuilt = build_apiwha_failed_event(
                our_phone_number=our_phone_number,
                raw_event=payload,
            )
        else:
            # apiwha doesn't have a "delivered/read" event in its webhook spec.
            return
    else:
        return

    delivery = await enqueue_delivery(
        db,
        arq_pool,
        organization_id=organization_id,
        whatsapp_number_id=number_id,
        target_url=webhook_url,
        secret=webhook_secret,
        event_type=event,
        instance_name=instance_name,
        raw_event_payload=payload,
        format="apiwha_neotel",
        prebuilt_payload=prebuilt,
    )
    logger.info(
        "apiwha delivery enqueued: %s for event %s (rapiwha=%s)",
        delivery.id,
        event,
        prebuilt.get("event"),
    )


async def _dispatch_neotel_custom(
    *,
    db: AsyncSession,
    arq_pool,
    organization_id,
    number_id,
    instance_name: str,
    event: str,
    payload: dict[str, Any],
    webhook_url: str,
    webhook_secret: str,
    webhook_extra: dict[str, Any],
    our_phone_number: str | None,
    upsert_result: dict[str, Any] | None,
) -> None:
    """Build the Custom Provider envelope and enqueue a delivery.

    Inbound MESSAGES_UPSERT goes to the Messages URL (provided by user).
    MESSAGES_UPDATE goes to the Events URL (derived from Messages URL by
    swapping the path segment).
    """
    from app.services.webhook_outbound import (
        build_neotel_event_payload,
        build_neotel_message_payload,
        derive_neotel_events_url,
        enqueue_delivery,
        hash_uuid_to_int,
    )

    account_id = (webhook_extra.get("account_id") or "").strip()
    if not account_id:
        logger.warning(
            "neotel_custom delivery skipped: number %s has no account_id in webhook_extra",
            number_id,
        )
        return

    if event == "MESSAGES_UPSERT":
        if not upsert_result or not upsert_result.get("conversation_id"):
            logger.warning(
                "neotel_custom delivery skipped: no conversation context for %s",
                number_id,
            )
            return
        prebuilt = build_neotel_message_payload(
            raw_event=payload,
            account_id=account_id,
            conversation_id_int=hash_uuid_to_int(
                upsert_result["conversation_id"]
            ),
            our_phone_number=our_phone_number,
            remote_phone=upsert_result.get("remote_phone"),
            remote_name=upsert_result.get("remote_name"),
            content_type=upsert_result.get("type"),
        )
        target_url = webhook_url
    elif event == "MESSAGES_UPDATE":
        prebuilt = build_neotel_event_payload(
            raw_event=payload,
            account_id=account_id,
        )
        if prebuilt is None:
            return
        target_url = derive_neotel_events_url(webhook_url)
    else:
        return

    await enqueue_delivery(
        db,
        arq_pool,
        organization_id=organization_id,
        whatsapp_number_id=number_id,
        target_url=target_url,
        secret=webhook_secret,
        event_type=event,
        instance_name=instance_name,
        raw_event_payload=payload,
        format="neotel_custom",
        prebuilt_payload=prebuilt,
    )


async def _handle_message_upsert(
    db: AsyncSession,
    number: WhatsAppNumber,
    data: dict[str, Any],
    full_payload: dict[str, Any],
) -> dict[str, Any]:
    key = data.get("key") or {}
    remote_jid = key.get("remoteJid")
    evolution_message_id = key.get("id")
    from_me = bool(key.get("fromMe"))

    if not remote_jid or not evolution_message_id:
        return {"skipped": "missing key.remoteJid or key.id"}

    # Pre-check for duplicate (idempotent: Evolution can retry the same event).
    existing = await db.execute(
        select(Message.id).where(
            Message.whatsapp_number_id == number.id,
            Message.evolution_message_id == evolution_message_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return {"deduped": evolution_message_id}

    conv = await _get_or_create_conversation(
        db, number, remote_jid, push_name=data.get("pushName")
    )

    content_type, text, media_url, media_mimetype = _extract_content(
        data.get("message")
    )
    timestamp = data.get("messageTimestamp")
    if isinstance(timestamp, (int, float)):
        sent_at = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    else:
        sent_at = datetime.now(timezone.utc)

    direction = "outbound" if from_me else "inbound"
    own_jid = (
        f"{number.phone_number}@s.whatsapp.net"
        if number.phone_number
        else number.instance_name
    )
    from_jid = own_jid if from_me else remote_jid
    to_jid = remote_jid if from_me else own_jid

    msg = Message(
        organization_id=number.organization_id,
        whatsapp_number_id=number.id,
        conversation_id=conv.id,
        direction=direction,
        evolution_message_id=evolution_message_id,
        from_jid=from_jid,
        to_jid=to_jid,
        content_type=content_type,
        content_text=text,
        media_url=media_url,
        media_mimetype=media_mimetype,
        raw_payload=full_payload,
        status="delivered" if direction == "inbound" else "sent",
        sent_at=sent_at,
    )
    db.add(msg)
    conv.last_message_at = sent_at
    await db.commit()
    await db.refresh(msg)
    return {
        "persisted_message_id": str(msg.id),
        "direction": direction,
        "type": content_type,
        "conversation_id": str(conv.id),
        "remote_name": conv.remote_name,
        "remote_phone": conv.remote_phone,
    }


async def _handle_message_update(
    db: AsyncSession, number: WhatsAppNumber, data: dict[str, Any]
) -> dict[str, Any]:
    """Update message status (sent → delivered → read)."""
    key = data.get("key") or {}
    evolution_message_id = key.get("id")
    new_status_raw = (data.get("status") or "").upper()

    mapping = {
        "PENDING": "pending",
        "SERVER_ACK": "sent",
        "DELIVERY_ACK": "delivered",
        "READ": "read",
        "PLAYED": "read",
        "ERROR": "failed",
    }
    new_status = mapping.get(new_status_raw)

    if not evolution_message_id or not new_status:
        return {"skipped": "no id or unknown status"}

    result = await db.execute(
        select(Message).where(
            Message.whatsapp_number_id == number.id,
            Message.evolution_message_id == evolution_message_id,
        )
    )
    msg = result.scalar_one_or_none()
    if msg is None:
        return {"skipped": "message not found"}

    msg.status = new_status
    await db.commit()
    return {"message_id": str(msg.id), "status": new_status}


async def _handle_connection_update(
    db: AsyncSession, number: WhatsAppNumber, data: dict[str, Any]
) -> dict[str, Any]:
    raw_state = data.get("state") or data.get("connection")
    new_status = map_state_to_status(raw_state)
    changed = False

    if new_status != number.status:
        number.status = new_status
        changed = True
        if new_status == "connected":
            number.last_connected_at = datetime.now(timezone.utc)

    # Try every JID-shaped field Evolution might send. Different Evolution
    # versions and event flavours expose the owner under different keys.
    if number.status == "connected" and not number.phone_number:
        for candidate in (
            data.get("wuid"),
            data.get("ownerJid"),
            data.get("owner"),
            data.get("number"),
            (data.get("instance") or {}).get("ownerJid"),
            (data.get("instance") or {}).get("owner"),
        ):
            phone = _extract_phone(candidate) if isinstance(candidate, str) else None
            if phone:
                number.phone_number = phone
                changed = True
                break

        # Last-resort: ask Evolution directly via fetchInstances.
        if not number.phone_number:
            from app.services.whatsapp_number import _try_capture_phone_from_evolution

            if await _try_capture_phone_from_evolution(db, number):
                changed = True

    if changed:
        await db.commit()

    return {
        "status": number.status,
        "raw_state": raw_state,
        "phone_number": number.phone_number,
    }
