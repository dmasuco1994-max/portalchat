"""Integration callbacks from external CRMs.

Phase 8.2: Neotel Custom Provider — Neotel POSTs here when an agent sends
a message from their UI. We dispatch via Evolution and return the SendResult
shape Neotel's documentation requires.

Endpoint:
    POST /api/v1/integrations/neotel/{account_id}/send?token=<secret>

Body (per Neotel Custom Provider spec):
    {
      "id": "MSG-OUT-...",
      "accountId": "<must match path>",
      "phoneNumber": "5491134567890",
      "body": "Hello",
      "type": "text" | "audio" | "image" | "video" | "file" | "intent",
      "CustomField1..5": "..."
    }

Response (success):
    {"SendResult": {"id": "MSG-OUT-...", "problems": null}}

Response (error):
    {"SendResult": {"id": null, "problems": {"code": 400, "message": "..."}}}
"""
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import DbSession
from app.models.whatsapp_number import WhatsAppNumber
from app.services.evolution import EvolutionAPIError, evolution_client


router = APIRouter(prefix="/integrations/neotel", tags=["integrations"])


class NeotelOutboundMessage(BaseModel):
    id: str = Field(..., description="Echoed back in SendResult.id on success.")
    accountId: str
    phoneNumber: str
    body: str = ""
    type: str = "text"
    CustomField1: str | None = None
    CustomField2: str | None = None
    CustomField3: str | None = None
    CustomField4: str | None = None
    CustomField5: str | None = None


def _ok(message_id: str) -> dict[str, Any]:
    return {"SendResult": {"id": message_id, "problems": None}}


def _err(code: int, message: str) -> dict[str, Any]:
    return {"SendResult": {"id": None, "problems": {"code": code, "message": message}}}


@router.post(
    "/{account_id}/send",
    summary=(
        "Neotel Custom Provider outbound callback. Authenticates via "
        "?token=<callback_token> matching webhook_extra.callback_token on "
        "the WhatsApp number whose webhook_extra.account_id equals the path."
    ),
)
async def neotel_send(
    account_id: str,
    payload: NeotelOutboundMessage,
    db: DbSession,
    token: str = Query(..., description="Per-account callback token."),
) -> dict[str, Any]:
    if payload.accountId != account_id:
        return _err(
            400,
            f"Body accountId ({payload.accountId}) does not match path ({account_id}).",
        )

    # Look up the WhatsApp number by account_id + token. We use JSONB ->> casts
    # so the match works regardless of which org owns the number — the token
    # is the per-account secret.
    result = await db.execute(
        select(WhatsAppNumber).where(
            WhatsAppNumber.webhook_format == "neotel_custom",
            WhatsAppNumber.webhook_extra["account_id"].astext == account_id,
            WhatsAppNumber.webhook_extra["callback_token"].astext == token,
        )
    )
    number = result.scalar_one_or_none()
    if number is None:
        # Don't leak whether account_id or token was wrong.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown account or invalid token.",
        )

    if number.status != "connected":
        return _err(
            409,
            f"WhatsApp number is not connected (status={number.status}).",
        )

    if payload.type != "text":
        return _err(
            415,
            f"Unsupported message type '{payload.type}'. Only 'text' is wired up.",
        )

    phone_digits = "".join(ch for ch in payload.phoneNumber if ch.isdigit())
    if not phone_digits:
        return _err(400, "phoneNumber must contain at least one digit.")
    if not payload.body:
        return _err(400, "body is required for type=text.")

    try:
        await evolution_client.send_text(
            number.instance_name,
            phone_digits,
            payload.body,
        )
    except EvolutionAPIError as exc:
        return _err(502, f"Evolution rejected the send: {exc.payload}")
    except Exception as exc:  # pragma: no cover — defensive
        return _err(500, f"Unexpected error: {type(exc).__name__}: {exc}")

    return _ok(payload.id)
