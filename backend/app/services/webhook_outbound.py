"""Outbound CRM webhook delivery — async, persistent, retried.

Phase 5 design:
  1. `enqueue_delivery` writes a WebhookDelivery row and dispatches an arq job
     pointing at it. Returns immediately.
  2. `process_webhook_delivery` (the arq task — defined here) loads the row,
     POSTs the signed payload, updates status/response/error, and reschedules
     itself with exponential backoff on failure.

Retry schedule (seconds): 5, 30, 120, 600, 1800. After max_attempts → 'abandoned'.

Phase 8 added `format`:
  - `portal` — our native JSON envelope + HMAC headers (Phase 5 default).
  - `apiwha_neotel` — form-encoded POST mimicking the apiwha webhook shape
    so Neotel's CAPIWHA provider slot can ingest us as if we were apiwha.
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.webhook_delivery import WebhookDelivery


logger = logging.getLogger(__name__)


# Retry delay in seconds for attempts 1..5. attempts is 1-indexed by the time
# the worker decides what to do next; index 0 is unused.
RETRY_DELAYS_SECONDS = [None, 5, 30, 120, 600, 1800]
ARQ_JOB_NAME = "process_webhook_delivery"
DELIVERY_TIMEOUT_SECONDS = 10


def _sign(secret: str, body_bytes: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()


def _build_envelope(event: str, instance: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "event": event,
        "instance": instance,
        "delivered_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }


# ---- apiwha / rapiwha adapter --------------------------------------------
# Matches the spec at https://panel.rapiwha.com/page_api.php:
#   POST <url>
#   Content-Type: application/x-www-form-urlencoded
#   Body: data=<URL-encoded JSON>
#
# Events:
#   INBOX            — inbound message from a contact
#   MESSAGEPROCESSED — our number's outbound message was accepted
#   MESSAGEFAILED    — our number's outbound message was rejected
def _phone_from_jid(jid: str | None) -> str:
    """Strip the @s.whatsapp.net suffix and any non-digit characters."""
    if not jid:
        return ""
    base = jid.split("@", 1)[0]
    return "".join(ch for ch in base if ch.isdigit())


def build_apiwha_inbox_event(
    *,
    our_phone_number: str | None,
    raw_event: dict[str, Any],
    remote_name: str | None = None,
) -> dict[str, Any]:
    """Inbound message → INBOX event payload (the JSON that goes inside the
    `data` form field)."""
    data = raw_event.get("data") or {}
    key = data.get("key") or {}
    message = data.get("message") or {}
    remote_phone = _phone_from_jid(key.get("remoteJid"))
    text = (
        message.get("conversation")
        or (message.get("extendedTextMessage") or {}).get("text")
        or ""
    )
    push_name = data.get("pushName") or remote_name or ""
    return {
        "event": "INBOX",
        "from": remote_phone,
        "to": our_phone_number or "",
        "text": text,
        "pushname": push_name,
        # `alias` and `profilepicture` are rapiwha extras that need the contact
        # book on the device. We don't have either reliably, so we omit them.
    }


def build_apiwha_processed_event(
    *,
    our_phone_number: str | None,
    raw_event: dict[str, Any],
    custom_data: str | None = None,
) -> dict[str, Any]:
    """Outbound message accepted → MESSAGEPROCESSED event."""
    data = raw_event.get("data") or {}
    key = data.get("key") or {}
    return {
        "event": "MESSAGEPROCESSED",
        "from": our_phone_number or "",
        "to": _phone_from_jid(key.get("remoteJid")),
        "custom_data": custom_data or "",
    }


def build_apiwha_failed_event(
    *,
    our_phone_number: str | None,
    raw_event: dict[str, Any],
    custom_data: str | None = None,
) -> dict[str, Any]:
    """Outbound message rejected → MESSAGEFAILED event."""
    data = raw_event.get("data") or {}
    key = data.get("key") or {}
    return {
        "event": "MESSAGEFAILED",
        "from": our_phone_number or "",
        "to": _phone_from_jid(key.get("remoteJid")),
        "custom_data": custom_data or "",
    }


# ---- neotel_custom adapter -----------------------------------------------
NEOTEL_CONTENT_TYPE_MAP = {
    "text": "chat",
    "image": "image",
    "audio": "audio",
    "video": "video",
    "document": "document",
    "sticker": "image",
    "ptt": "ptt",
}

NEOTEL_STATUS_MAP = {
    "PENDING": "received",
    "SERVER_ACK": "received",
    "DELIVERY_ACK": "delivered",
    "READ": "read",
    "PLAYED": "viewed",
}


def hash_uuid_to_int(uuid_str: str | None) -> int:
    """Map a UUID string to a stable positive 31-bit integer.

    Neotel's Custom Provider requires `conversationId` as an integer; our
    conversations are UUIDs. We hash to a 31-bit range so the value fits in
    every typical signed-int column (Java/SQL Server-friendly) and stays
    positive. Deterministic across deliveries and processes.
    """
    if not uuid_str:
        return 0
    digest = hashlib.blake2b(uuid_str.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, "big") & 0x7FFFFFFF


def derive_neotel_events_url(messages_url: str) -> str:
    """The user pastes the Messages URL; the Events URL is the same path with
    /Messages/ → /Events/. Apply once."""
    return messages_url.replace("/Messages/", "/Events/", 1)


def build_neotel_message_payload(
    *,
    raw_event: dict[str, Any],
    account_id: str,
    conversation_id_int: int,
    our_phone_number: str | None,
    remote_phone: str | None,
    remote_name: str | None,
    content_type: str | None,
) -> dict[str, Any]:
    """Inbound message → Neotel CustomAccount/Messages payload."""
    data = raw_event.get("data") or {}
    key = data.get("key") or {}
    message = data.get("message") or {}
    text = (
        message.get("conversation")
        or (message.get("extendedTextMessage") or {}).get("text")
        or ""
    )
    ts = data.get("messageTimestamp") or data.get("messageTimestampMs")
    if isinstance(ts, (int, float)):
        if ts > 10_000_000_000:
            time_ms = int(ts)
        else:
            time_ms = int(ts * 1000)
    else:
        time_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    neotel_type = NEOTEL_CONTENT_TYPE_MAP.get(content_type or "text", "chat")

    return {
        "accountId": account_id,
        "messages": [
            {
                "id": str(key.get("id") or ""),
                "body": text,
                "caption": "",
                "type": neotel_type,
                "contactName": remote_name or remote_phone or "",
                "contactNumber": remote_phone or "",
                "time": time_ms,
                "conversationId": conversation_id_int,
                "isBot": False,
            }
        ],
    }


def build_external_neotel_payload(
    *,
    raw_event: dict[str, Any],
    application_id: str,
    remote_phone: str | None,
    remote_name: str | None,
    content_type: str | None,
    message_uuid: str | None,
) -> dict[str, Any]:
    """Inbound WhatsApp message → Neotel ExternalApplication Message Entity.

    Spec: https://neotel-us.atlassian.net/wiki/spaces/NEOT/pages/6358021
    POST `<base>/api/ExternalApplication/SendMessage` with headers
    `ApplicationId` + `AccessToken` and this JSON body.
    """
    data = raw_event.get("data") or {}
    key = data.get("key") or {}
    message = data.get("message") or {}
    text = (
        message.get("conversation")
        or (message.get("extendedTextMessage") or {}).get("text")
        or ""
    )
    ts = data.get("messageTimestamp") or data.get("messageTimestampMs")
    if isinstance(ts, (int, float)):
        if ts > 10_000_000_000:
            ts = ts / 1000
        creation = datetime.fromtimestamp(ts, tz=timezone.utc)
    else:
        creation = datetime.now(timezone.utc)

    return {
        "id": str(key.get("id") or ""),
        "creationTime": creation.isoformat(),
        "text": text,
        "contactId": remote_phone or "",
        "contactName": remote_name or remote_phone or "Unknown",
        "contactLastName": "",
        "contactEmail": "",
        "contactImgProfile": "",
        "observations": "",
        "crm": None,
        "crmId": "",
        "externalId": message_uuid or "",
        "isInbound": True,
        "accountId": application_id,
        "attachment": None,
    }


def build_neotel_event_payload(
    *,
    raw_event: dict[str, Any],
    account_id: str,
) -> dict[str, Any] | None:
    """Status update (MESSAGES_UPDATE) → Neotel CustomAccount/Events payload.
    Returns None when the Evolution status doesn't map to a Neotel status."""
    data = raw_event.get("data") or {}
    key = data.get("key") or {}
    raw_status = (data.get("status") or "").upper()
    neotel_status = NEOTEL_STATUS_MAP.get(raw_status)
    if neotel_status is None:
        return None
    return {
        "InstanceId": account_id,
        "events": [
            {
                "id": str(key.get("id") or ""),
                "status": neotel_status,
            }
        ],
    }


# ---- Enqueue (called from the inbound webhook handler) -------------------
async def enqueue_delivery(
    db,
    arq_pool,
    *,
    organization_id: UUID,
    whatsapp_number_id: UUID,
    target_url: str,
    secret: str,
    event_type: str,
    instance_name: str,
    raw_event_payload: dict[str, Any],
    max_attempts: int = 5,
    format: str = "portal",
    prebuilt_payload: dict[str, Any] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> WebhookDelivery:
    """Persist a delivery row and dispatch an arq job for it.

    The body stored in `payload` depends on `format`:
      - portal → our envelope (UUID + event + raw payload)
      - apiwha_neotel → caller pre-builds an event dict (INBOX / MESSAGEPROCESSED
        / MESSAGEFAILED). At dispatch time it's wrapped as `data=<json>` form.
      - neotel_custom → caller pre-builds the JSON via `prebuilt_payload`
      - external_neotel → caller pre-builds the Message Entity JSON and passes
        `extra_headers` with ApplicationId + AccessToken.
    """
    if prebuilt_payload is not None:
        snapshot = prebuilt_payload
    else:
        snapshot = _build_envelope(event_type, instance_name, raw_event_payload)

    row = WebhookDelivery(
        organization_id=organization_id,
        whatsapp_number_id=whatsapp_number_id,
        target_url=target_url,
        event_type=event_type,
        payload=snapshot,
        secret=secret,
        format=format,
        extra_headers=extra_headers,
        max_attempts=max_attempts,
        status="pending",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    if arq_pool is not None:
        try:
            await arq_pool.enqueue_job(ARQ_JOB_NAME, str(row.id))
        except Exception as exc:
            logger.error(
                "Failed to dispatch arq job for delivery %s: %s",
                row.id,
                exc,
            )
    else:
        logger.warning(
            "arq pool not configured; delivery %s queued but no worker will run it",
            row.id,
        )
    return row


# ---- Worker task (loaded by arq_worker.WorkerSettings) -------------------
async def process_webhook_delivery(ctx: dict, delivery_id: str) -> dict[str, Any]:
    """One delivery attempt. Updates the row in-place; reschedules on failure."""
    arq_pool = ctx["redis"]
    delivery_uuid = UUID(delivery_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WebhookDelivery).where(WebhookDelivery.id == delivery_uuid)
        )
        row: WebhookDelivery | None = result.scalar_one_or_none()
        if row is None:
            logger.warning("Delivery %s vanished before worker picked it up", delivery_id)
            return {"status": "missing"}
        if row.status in ("success", "abandoned"):
            return {"status": row.status, "noop": True}

        row.status = "in_progress"
        row.last_attempt_at = datetime.now(timezone.utc)
        row.attempts += 1
        await db.commit()

        attempt_n = row.attempts

        if row.format == "apiwha_neotel":
            # rapiwha spec: POST form-encoded with a SINGLE `data` field whose
            # value is the JSON-encoded event. Receivers read $_POST["data"].
            body_bytes = urlencode(
                {"data": json.dumps(row.payload, separators=(",", ":"))}
            ).encode("utf-8")
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-WhatsApp-Portal-Delivery": str(row.id),
                "X-WhatsApp-Portal-Attempt": str(attempt_n),
            }
        elif row.format == "neotel_custom":
            body_bytes = json.dumps(row.payload, separators=(",", ":")).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "X-WhatsApp-Portal-Delivery": str(row.id),
                "X-WhatsApp-Portal-Attempt": str(attempt_n),
            }
        elif row.format == "external_neotel":
            body_bytes = json.dumps(row.payload, separators=(",", ":")).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "X-WhatsApp-Portal-Delivery": str(row.id),
                "X-WhatsApp-Portal-Attempt": str(attempt_n),
            }
            if row.extra_headers:
                # ApplicationId + AccessToken, per Neotel's spec.
                for k, v in row.extra_headers.items():
                    headers[k] = str(v)
        else:
            body_bytes = json.dumps(row.payload, separators=(",", ":")).encode("utf-8")
            signature = _sign(row.secret, body_bytes)
            delivery_uuid_str = row.payload.get("id", str(row.id))
            headers = {
                "Content-Type": "application/json",
                "X-WhatsApp-Portal-Signature": f"sha256={signature}",
                "X-WhatsApp-Portal-Event": row.event_type,
                "X-WhatsApp-Portal-Delivery": delivery_uuid_str,
                "X-WhatsApp-Portal-Attempt": str(attempt_n),
            }

        try:
            async with httpx.AsyncClient(timeout=DELIVERY_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    row.target_url,
                    content=body_bytes,
                    headers=headers,
                )
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            return await _handle_delivery_failure(
                db, arq_pool, row, error_message=f"{type(exc).__name__}: {exc}"
            )

        excerpt = (response.text or "")[:2000]
        row.response_status = response.status_code
        row.response_body_excerpt = excerpt

        if 200 <= response.status_code < 300:
            row.status = "success"
            row.completed_at = datetime.now(timezone.utc)
            row.error_message = None
            row.next_retry_at = None
            await db.commit()
            return {"status": "success", "code": response.status_code}

        return await _handle_delivery_failure(
            db,
            arq_pool,
            row,
            error_message=f"HTTP {response.status_code}",
        )


async def _handle_delivery_failure(
    db, arq_pool, row: WebhookDelivery, *, error_message: str
) -> dict[str, Any]:
    row.error_message = error_message
    if row.attempts >= row.max_attempts:
        row.status = "abandoned"
        row.next_retry_at = None
        row.completed_at = datetime.now(timezone.utc)
        await db.commit()
        logger.error(
            "Delivery %s ABANDONED after %d attempts: %s",
            row.id,
            row.attempts,
            error_message,
        )
        return {"status": "abandoned", "attempts": row.attempts}

    delay = RETRY_DELAYS_SECONDS[
        min(row.attempts, len(RETRY_DELAYS_SECONDS) - 1)
    ]
    row.status = "failed"
    row.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
    await db.commit()

    if arq_pool is not None:
        try:
            await arq_pool.enqueue_job(
                ARQ_JOB_NAME,
                str(row.id),
                _defer_by=timedelta(seconds=delay),
            )
        except Exception as exc:
            logger.error(
                "Failed to schedule retry for delivery %s: %s", row.id, exc
            )

    logger.warning(
        "Delivery %s failed (attempt %d/%d) — retry in %ds: %s",
        row.id,
        row.attempts,
        row.max_attempts,
        delay,
        error_message,
    )
    return {"status": "failed", "attempt": row.attempts, "next_retry_in_seconds": delay}
