"""Outbound CRM webhook delivery — async, persistent, retried.

Phase 5 design:
  1. `enqueue_delivery` writes a WebhookDelivery row and dispatches an arq job
     pointing at it. Returns immediately.
  2. `process_webhook_delivery` (the arq task — defined here) loads the row,
     POSTs the signed payload, updates status/response/error, and reschedules
     itself with exponential backoff on failure.

Retry schedule (seconds): 5, 30, 120, 600, 1800. After max_attempts → 'abandoned'.
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
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
) -> WebhookDelivery:
    """Persist a delivery row and dispatch an arq job for it."""
    envelope = _build_envelope(event_type, instance_name, raw_event_payload)

    row = WebhookDelivery(
        organization_id=organization_id,
        whatsapp_number_id=whatsapp_number_id,
        target_url=target_url,
        event_type=event_type,
        payload=envelope,
        secret=secret,
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
        body_bytes = json.dumps(row.payload, separators=(",", ":")).encode("utf-8")
        signature = _sign(row.secret, body_bytes)
        delivery_uuid_str = row.payload.get("id", str(row.id))

        try:
            async with httpx.AsyncClient(timeout=DELIVERY_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    row.target_url,
                    content=body_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-WhatsApp-Portal-Signature": f"sha256={signature}",
                        "X-WhatsApp-Portal-Event": row.event_type,
                        "X-WhatsApp-Portal-Delivery": delivery_uuid_str,
                        "X-WhatsApp-Portal-Attempt": str(attempt_n),
                    },
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
