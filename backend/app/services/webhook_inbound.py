"""Receive and process Evolution API webhook events.

Responsibilities:
  1. Identify the WhatsAppNumber by instance_name
  2. Persist incoming/outgoing messages (deduped by evolution_message_id)
  3. Update connection status when CONNECTION_UPDATE fires
  4. Forward the event to the tenant's configured CRM webhook (sync, Phase 4)

Sync delivery to CRM is intentional for Phase 4 — Phase 5 will introduce an
async queue with retries and HMAC-signed deliveries.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.whatsapp_number import WhatsAppNumber
from app.services.evolution import map_state_to_status
from app.services.webhook_outbound import enqueue_delivery


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


def _extract_text_and_type(message_payload: dict[str, Any] | None) -> tuple[str, str | None]:
    """Returns (content_type, text or None)."""
    if not message_payload:
        return "unknown", None

    if "conversation" in message_payload:
        return "text", message_payload["conversation"]
    if "extendedTextMessage" in message_payload:
        return "text", message_payload["extendedTextMessage"].get("text")
    if "imageMessage" in message_payload:
        return "image", message_payload["imageMessage"].get("caption")
    if "videoMessage" in message_payload:
        return "video", message_payload["videoMessage"].get("caption")
    if "audioMessage" in message_payload:
        return "audio", None
    if "documentMessage" in message_payload:
        return "document", message_payload["documentMessage"].get("fileName")
    if "stickerMessage" in message_payload:
        return "sticker", None
    if "locationMessage" in message_payload:
        return "location", None
    if "contactMessage" in message_payload or "contactsArrayMessage" in message_payload:
        return "contact", None
    if "reactionMessage" in message_payload:
        return "reaction", message_payload["reactionMessage"].get("text")
    return "unknown", None


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
    elif push_name and conv.remote_name != push_name:
        conv.remote_name = push_name
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
        should_deliver = not webhook_events or event in [
            e.upper() for e in webhook_events
        ]
        if webhook_format == "apiwha_neotel":
            # apiwha emulation only forwards inbound text-style messages. Outbound
            # echoes (fromMe) and non-message events would confuse Neotel's parser.
            key = (data.get("key") or {}) if isinstance(data, dict) else {}
            should_deliver = (
                event == "MESSAGES_UPSERT" and not bool(key.get("fromMe"))
            )
        elif webhook_format == "neotel_custom":
            # Custom Provider only cares about inbound messages and status updates.
            key = (data.get("key") or {}) if isinstance(data, dict) else {}
            if event == "MESSAGES_UPSERT":
                should_deliver = not bool(key.get("fromMe"))
            elif event == "MESSAGES_UPDATE":
                should_deliver = True
            else:
                should_deliver = False

        if should_deliver and webhook_format == "neotel_custom":
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

        if should_deliver:
            apikey_token = webhook_extra.get("token") if isinstance(
                webhook_extra.get("token"), str
            ) else None
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
                our_phone_number=our_phone_number,
                apikey=apikey_token,
            )
            summary["crm_delivery_id"] = str(delivery.id)
            summary["crm_delivery_status"] = delivery.status

    return summary


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

    content_type, text = _extract_text_and_type(data.get("message"))
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
