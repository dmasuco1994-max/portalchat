"""rapiwha (ex-apiwha) API drop-in replacement.

Exposes the public endpoints rapiwha publishes at the root of `panel.rapiwha.com`
so a CRM like Neotel — which has the apiwha host pre-wired into its
SocialMedia service — can call our backend instead by repointing the host.

Endpoints mounted at ROOT (no /api/v1 prefix):

  GET|POST /send_message.php   — send a WhatsApp message via Evolution
  GET      /get_credit.php     — credit query (we return a synthetic value)
  GET      /get_messages.php   — pull stored messages (basic; CRMs that use
                                 the webhook path won't need it)

Authentication: every endpoint requires `apikey` matching the
`webhook_extra.token` saved on a WhatsApp number whose `webhook_format` is
`apiwha_neotel`.

Spec source: https://panel.rapiwha.com/page_api.php (per-user docs).
"""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import DbSession
from app.models.message import Message
from app.models.whatsapp_number import WhatsAppNumber
from app.services.evolution import EvolutionAPIError, evolution_client


router = APIRouter(tags=["apiwha-compat"])


# Result codes copied verbatim from rapiwha's docs.
RC_OK = 0
RC_INVALID_APIKEY = -1
RC_MISSING_PARAMS = -2
RC_TRIAL_NEVER_WROTE = -3
RC_RATE_LIMITED = -5
RC_NOT_READY = -6
RC_INVALID_UTF8 = -8
RC_SELF_SEND = -9
RC_NO_CREDIT = -10
RC_QUEUE_FULL = -11


def _response(success: bool, description: str, code: int) -> dict[str, Any]:
    return {"success": success, "description": description, "result_code": code}


async def _lookup_number_by_apikey(db: AsyncSession, apikey: str) -> WhatsAppNumber | None:
    result = await db.execute(
        select(WhatsAppNumber).where(
            WhatsAppNumber.webhook_format == "apiwha_neotel",
            WhatsAppNumber.webhook_extra["token"].astext == apikey,
        )
    )
    return result.scalar_one_or_none()


async def _send_message_impl(
    db: AsyncSession,
    apikey: str | None,
    number: str | None,
    text: str | None,
    custom_data: str | None,
) -> dict[str, Any]:
    """Shared logic for GET and POST variants of /send_message.php."""
    if not apikey:
        return _response(False, "Invalid apikey", RC_INVALID_APIKEY)
    if not number or not text:
        return _response(
            False, "Missing parameters (number and text are required)", RC_MISSING_PARAMS
        )
    try:
        text.encode("utf-8")
    except UnicodeError:
        return _response(False, "Text must be UTF-8 encoded", RC_INVALID_UTF8)

    found = await _lookup_number_by_apikey(db, apikey)
    if found is None:
        return _response(False, "Invalid apikey", RC_INVALID_APIKEY)

    if found.status != "connected":
        return _response(
            False,
            f"Your Apikey is not ready yet (number status: {found.status})",
            RC_NOT_READY,
        )

    phone_digits = "".join(ch for ch in number if ch.isdigit())
    if not phone_digits:
        return _response(False, "number must contain at least one digit", RC_MISSING_PARAMS)

    if found.phone_number and phone_digits == found.phone_number:
        return _response(False, "You cannot send a message to yourself", RC_SELF_SEND)

    try:
        await evolution_client.send_text(found.instance_name, phone_digits, text)
    except EvolutionAPIError as exc:
        return _response(
            False,
            f"Evolution rejected the send: {exc.payload}",
            RC_RATE_LIMITED,
        )
    except Exception as exc:  # pragma: no cover — defensive
        return _response(False, f"Internal error: {type(exc).__name__}", RC_RATE_LIMITED)

    # custom_data round-trip would require storing it against the outbound
    # message we'll see echoed via Evolution's SEND_MESSAGE webhook. Out of
    # scope for v1; we accept it but don't persist.
    return _response(True, "Message queued", RC_OK)


@router.api_route("/send_message.php", methods=["GET", "POST"])
async def send_message(
    request: Request,
    db: DbSession,
    apikey_q: str | None = Query(default=None, alias="apikey"),
    number_q: str | None = Query(default=None, alias="number"),
    text_q: str | None = Query(default=None, alias="text"),
    custom_data_q: str | None = Query(default=None, alias="custom_data"),
) -> dict[str, Any]:
    """rapiwha send_message.php drop-in. Accepts params from query string
    (GET) or form-data (POST). Returns the rapiwha JSON envelope."""
    apikey, number_, text_, custom_data = apikey_q, number_q, text_q, custom_data_q
    if request.method == "POST":
        try:
            form = await request.form()
        except Exception:
            form = None
        if form:
            apikey = form.get("apikey") or apikey
            number_ = form.get("number") or number_
            text_ = form.get("text") or text_
            custom_data = form.get("custom_data") or custom_data

    return await _send_message_impl(
        db,
        apikey=apikey,
        number=number_,
        text=text_,
        custom_data=custom_data,
    )


@router.get("/get_credit.php")
async def get_credit(
    db: DbSession,
    apikey: str = Query(...),
) -> dict[str, Any]:
    """rapiwha get_credit.php drop-in. We don't run a credit ledger, so we
    return a large synthetic balance to keep CRMs from refusing to send."""
    found = await _lookup_number_by_apikey(db, apikey)
    if found is None:
        # rapiwha returns 0 / error JSON; mirror that.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid apikey")
    return {"credit": 9999}


@router.get("/get_messages.php")
async def get_messages(
    db: DbSession,
    apikey: str = Query(...),
    type: str | None = Query(default=None),
    number: str | None = Query(default=None),
    custom_data: str | None = Query(default=None),
    markaspulled: int | None = Query(default=None),
    getnotpulledonly: int | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    """rapiwha get_messages.php drop-in. Returns the saved messages for the
    number identified by the apikey, in the apiwha shape."""
    found = await _lookup_number_by_apikey(db, apikey)
    if found is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid apikey")

    stmt = select(Message).where(Message.whatsapp_number_id == found.id)
    if type and type.upper() == "IN":
        stmt = stmt.where(Message.direction == "inbound")
    elif type and type.upper() == "OUT":
        stmt = stmt.where(Message.direction == "outbound")
    stmt = stmt.order_by(Message.sent_at.desc()).limit(500)

    result = await db.execute(stmt)
    out: list[dict[str, Any]] = []
    for msg in result.scalars().all():
        digits_from = "".join(ch for ch in (msg.from_jid or "").split("@")[0] if ch.isdigit())
        digits_to = "".join(ch for ch in (msg.to_jid or "").split("@")[0] if ch.isdigit())
        out.append(
            {
                "id": str(msg.id),
                "number": found.phone_number or "",
                "from": digits_from,
                "to": digits_to,
                "type": "IN" if msg.direction == "inbound" else "OUT",
                "text": msg.content_text or "",
                "creation_date": msg.sent_at.strftime("%Y-%m-%d %H:%M:%S")
                if msg.sent_at
                else "",
                "process_date": msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if msg.created_at
                else "",
                "custom_data": None,
            }
        )
    return out
