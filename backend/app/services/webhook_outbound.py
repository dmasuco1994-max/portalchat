"""Deliver events to a tenant's CRM webhook.

Phase 4: SYNCHRONOUS delivery with HMAC-SHA256 signing.
Phase 5: will move to an async queue (arq) with retries and exponential backoff.
"""
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx


def _sign(secret: str, body_bytes: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()


async def deliver_to_crm(
    url: str,
    secret: str,
    event: str,
    instance: str,
    payload: dict[str, Any],
    timeout: float = 5.0,
) -> dict[str, Any]:
    """POST a signed payload to the tenant's CRM webhook.

    The signature lives in `X-WhatsApp-Portal-Signature` as `sha256=<hex>`.
    The CRM should HMAC the raw request body with the shared secret and compare.
    """
    envelope = {
        "id": str(uuid4()),
        "event": event,
        "instance": instance,
        "delivered_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    body_bytes = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
    signature = _sign(secret, body_bytes)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            url,
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-WhatsApp-Portal-Signature": f"sha256={signature}",
                "X-WhatsApp-Portal-Event": event,
                "X-WhatsApp-Portal-Instance": instance,
                "X-WhatsApp-Portal-Delivery": envelope["id"],
            },
        )

    return {
        "status_code": response.status_code,
        "delivery_id": envelope["id"],
    }
