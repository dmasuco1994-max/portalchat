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


# ---- Neotel External Application callback --------------------------------
# Spec: https://neotel-us.atlassian.net/wiki/spaces/NEOT/pages/6358021
# When an agent in Neotel sends a message to a contact, Neotel POSTs the
# Message Entity to this endpoint (the one the user pasted into Neotel's
# `Webhook URL` field of the "Aplicación Externa" config).
class NeotelExternalMessage(BaseModel):
    id: str | None = None
    creationTime: str | None = None
    text: str | None = None
    contactId: str
    contactName: str | None = None
    contactLastName: str | None = None
    contactEmail: str | None = None
    contactImgProfile: str | None = None
    observations: str | None = None
    crm: int | None = None
    crmId: str | None = None
    externalId: str | None = None
    isInbound: bool | int | None = None
    accountId: str
    attachment: dict[str, Any] | None = None


@router.post(
    "/external/{application_id}/inbox",
    summary=(
        "Neotel External Application callback. Receives the Message Entity "
        "when an agent sends a reply from Neotel, dispatches it via Evolution."
    ),
)
async def neotel_external_inbox(
    application_id: str,
    payload: NeotelExternalMessage,
    db: DbSession,
    token: str = Query(..., description="Per-account callback token."),
) -> dict[str, Any]:
    if payload.accountId != application_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Body accountId does not match path application_id.",
        )

    # Ignore echoes of our own inbound messages (Neotel will resend the same
    # entity we sent it; treat those as no-ops).
    is_inbound = (
        bool(payload.isInbound)
        if isinstance(payload.isInbound, bool)
        else (payload.isInbound == 1)
    )
    if is_inbound:
        return {"success": True, "noop": "isInbound=true is not an agent reply"}

    result = await db.execute(
        select(WhatsAppNumber).where(
            WhatsAppNumber.webhook_format == "external_neotel",
            WhatsAppNumber.webhook_extra["application_id"].astext == application_id,
            WhatsAppNumber.webhook_extra["callback_token"].astext == token,
        )
    )
    number = result.scalar_one_or_none()
    if number is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown application or invalid token.",
        )

    if number.status != "connected":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"WhatsApp number is not connected (status={number.status}).",
        )

    if payload.attachment is not None:
        # Attachments would require uploading the base64 to Evolution's media
        # endpoint. Out of scope for v1.
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Attachments not yet supported — only text messages.",
        )

    if not payload.text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="text is required when no attachment is provided.",
        )

    phone_digits = "".join(ch for ch in payload.contactId if ch.isdigit())
    if not phone_digits:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="contactId must contain at least one digit.",
        )

    try:
        await evolution_client.send_text(
            number.instance_name,
            phone_digits,
            payload.text,
        )
    except EvolutionAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Evolution rejected the send: {exc.payload}",
        ) from exc

    return {"success": True, "id": payload.id}
