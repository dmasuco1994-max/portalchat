"""WhatsApp number orchestration: keeps our DB in sync with Evolution instances."""
import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.whatsapp_number import WhatsAppNumber
from app.schemas.whatsapp_number import WebhookConfigUpdate, WhatsAppNumberCreate
from app.services.evolution import (
    EvolutionAPIError,
    evolution_client,
    map_state_to_status,
)


logger = logging.getLogger(__name__)


def _generate_instance_name() -> str:
    return f"wp_{secrets.token_hex(6)}"


def _webhook_callback_url(instance_name: str) -> str:
    base = settings.public_backend_url.rstrip("/")
    return f"{base}/api/v1/webhooks/evolution/{instance_name}"


def _phone_from_jid(jid: str | None) -> str | None:
    if not jid:
        return None
    digits = "".join(ch for ch in jid.split("@")[0] if ch.isdigit())
    return digits or None


async def _try_capture_phone_from_evolution(
    db: AsyncSession, number: WhatsAppNumber
) -> bool:
    """Best-effort lookup of the connected phone via /instance/fetchInstances.
    Returns True if phone_number was updated.
    """
    try:
        info = await evolution_client.fetch_instance_info(number.instance_name)
    except EvolutionAPIError as exc:
        logger.warning(
            "fetch_instance_info failed for %s: %s",
            number.instance_name,
            exc.payload,
        )
        return False

    if not info:
        return False

    candidates = (
        info.get("ownerJid"),
        info.get("owner"),
        info.get("number"),
        (info.get("instance") or {}).get("ownerJid"),
        (info.get("instance") or {}).get("owner"),
    )
    for candidate in candidates:
        phone = _phone_from_jid(candidate) if isinstance(candidate, str) else None
        if phone:
            if number.phone_number != phone:
                number.phone_number = phone
                return True
            return False
    return False


async def list_numbers(
    db: AsyncSession, organization_id: UUID
) -> list[WhatsAppNumber]:
    result = await db.execute(
        select(WhatsAppNumber)
        .where(WhatsAppNumber.organization_id == organization_id)
        .order_by(WhatsAppNumber.created_at)
    )
    return list(result.scalars().all())


async def get_number(
    db: AsyncSession, organization_id: UUID, number_id: UUID
) -> WhatsAppNumber:
    result = await db.execute(
        select(WhatsAppNumber).where(
            WhatsAppNumber.id == number_id,
            WhatsAppNumber.organization_id == organization_id,
        )
    )
    number = result.scalar_one_or_none()
    if number is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WhatsApp number not found",
        )
    return number


async def get_number_by_instance(
    db: AsyncSession, instance_name: str
) -> WhatsAppNumber | None:
    result = await db.execute(
        select(WhatsAppNumber).where(WhatsAppNumber.instance_name == instance_name)
    )
    return result.scalar_one_or_none()


async def _subscribe_evolution_webhook(number: WhatsAppNumber) -> dict | None:
    """Subscribe Evolution to our backend webhook for this instance.

    Returns the Evolution response dict on success, None on failure (logs the error).
    Does not raise — callers decide whether to surface the error.
    """
    url = _webhook_callback_url(number.instance_name)
    try:
        response = await evolution_client.set_webhook(number.instance_name, url=url)
        logger.info(
            "Webhook subscribed: instance=%s url=%s",
            number.instance_name,
            url,
        )
        return response
    except EvolutionAPIError as exc:
        logger.error(
            "set_webhook FAILED for instance=%s url=%s status=%s payload=%s",
            number.instance_name,
            url,
            exc.status_code,
            exc.payload,
        )
        return None


async def create_number(
    db: AsyncSession,
    organization_id: UUID,
    payload: WhatsAppNumberCreate,
) -> WhatsAppNumber:
    for _ in range(5):
        instance_name = _generate_instance_name()
        number = WhatsAppNumber(
            organization_id=organization_id,
            name=payload.name,
            instance_name=instance_name,
            status="created",
        )
        db.add(number)
        try:
            await db.flush()
            break
        except IntegrityError:
            await db.rollback()
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not allocate a unique instance name",
        )

    try:
        await evolution_client.create_instance(number.instance_name)
    except EvolutionAPIError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Evolution API rejected instance creation: {exc.payload}",
        ) from exc

    # Subscribe Evolution to our backend webhook URL.
    # Failure here is non-fatal — admin can call POST /numbers/{id}/rebind-webhook
    # to retry later. We log loudly so the failure is visible in container logs.
    await _subscribe_evolution_webhook(number)

    await db.commit()
    await db.refresh(number)
    return number


async def rebind_webhook(
    db: AsyncSession, organization_id: UUID, number_id: UUID
) -> dict:
    """Force re-subscription of Evolution → our backend for this number.
    Use when initial subscription failed (check container logs) or after
    Evolution data was reset.
    """
    number = await get_number(db, organization_id, number_id)
    response = await _subscribe_evolution_webhook(number)
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Evolution rejected the webhook subscription. "
                "Check backend logs for details."
            ),
        )
    return {
        "instance_name": number.instance_name,
        "url": response.get("url"),
        "events": response.get("events"),
        "enabled": response.get("enabled"),
    }


async def fetch_qr(
    db: AsyncSession, organization_id: UUID, number_id: UUID
) -> dict:
    number = await get_number(db, organization_id, number_id)
    try:
        response = await evolution_client.connect_instance(number.instance_name)
    except EvolutionAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Evolution API error: {exc.payload}",
        ) from exc

    qr_base64 = response.get("base64") or response.get("qrcode", {}).get("base64")
    # Only the real human-typeable pairingCode. Evolution v2's `code` field
    # is the raw QR base64 blob (long, comma-separated, NOT a pair code) —
    # surfacing it to the UI rendered a wall of garbage.
    pairing_code = response.get("pairingCode")
    if isinstance(pairing_code, str):
        pairing_code = pairing_code.strip() or None
    else:
        pairing_code = None

    if number.status != "connected":
        number.status = "connecting"
        await db.commit()
        await db.refresh(number)

    return {
        "instance_name": number.instance_name,
        "status": number.status,
        "qr_base64": qr_base64,
        "pairing_code": pairing_code,
    }


async def sync_connection_status(
    db: AsyncSession, organization_id: UUID, number_id: UUID
) -> dict:
    number = await get_number(db, organization_id, number_id)
    try:
        response = await evolution_client.connection_state(number.instance_name)
    except EvolutionAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Evolution API error: {exc.payload}",
        ) from exc

    instance_section = response.get("instance") or response
    raw_state = (
        instance_section.get("state")
        or instance_section.get("connectionStatus")
        or instance_section.get("status")
    )
    new_status = map_state_to_status(raw_state)
    changed = False

    if new_status != number.status:
        number.status = new_status
        changed = True
        if new_status == "connected":
            number.last_connected_at = datetime.now(timezone.utc)

    # /instance/connectionState/ doesn't expose ownerJid, so when we believe
    # we're connected but still missing the phone, hit /instance/fetchInstances.
    if number.status == "connected" and not number.phone_number:
        if await _try_capture_phone_from_evolution(db, number):
            changed = True

    if changed:
        await db.commit()
        await db.refresh(number)

    return {
        "instance_name": number.instance_name,
        "status": number.status,
        "raw_state": raw_state,
    }


async def disconnect_number(
    db: AsyncSession, organization_id: UUID, number_id: UUID
) -> WhatsAppNumber:
    number = await get_number(db, organization_id, number_id)
    try:
        await evolution_client.logout_instance(number.instance_name)
    except EvolutionAPIError as exc:
        if exc.status_code not in (400, 404):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Evolution API error: {exc.payload}",
            ) from exc
    number.status = "disconnected"
    await db.commit()
    await db.refresh(number)
    return number


async def delete_number(
    db: AsyncSession, organization_id: UUID, number_id: UUID
) -> None:
    number = await get_number(db, organization_id, number_id)
    try:
        await evolution_client.delete_instance(number.instance_name)
    except EvolutionAPIError as exc:
        if exc.status_code not in (400, 404):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Evolution API error: {exc.payload}",
            ) from exc
    await db.delete(number)
    await db.commit()


async def update_webhook_config(
    db: AsyncSession,
    organization_id: UUID,
    number_id: UUID,
    payload: WebhookConfigUpdate,
) -> tuple[WhatsAppNumber, str | None]:
    number = await get_number(db, organization_id, number_id)

    if payload.url is None:
        number.webhook_url = None
        number.webhook_events = None
        number.webhook_active = False
        number.webhook_secret = None
        number.webhook_format = "portal"
        number.webhook_extra = None
        await db.commit()
        await db.refresh(number)
        return number, None

    # apiwha_neotel doesn't sign with our HMAC, but we still need *something*
    # in webhook_secret because the inbound handler gates on its truthiness.
    # Use a sentinel so future rotates still work the same way.
    new_secret_plain: str | None = None
    if payload.format in ("apiwha_neotel", "neotel_custom", "external_neotel"):
        if number.webhook_secret is None or payload.rotate_secret:
            # Generate a placeholder; not used for signing in these formats.
            number.webhook_secret = secrets.token_urlsafe(16)
    else:
        if number.webhook_secret is None or payload.rotate_secret:
            new_secret_plain = secrets.token_urlsafe(32)
            number.webhook_secret = new_secret_plain

    # For neotel_custom + external_neotel, generate a callback_token the user
    # pastes into Neotel's Webhook URL config as `?token=...`. Rotate only when
    # explicitly requested or on first save.
    extra = dict(payload.extra or {})
    if payload.format in ("neotel_custom", "external_neotel"):
        existing_extra = dict(number.webhook_extra or {})
        existing_token = existing_extra.get("callback_token")
        if not isinstance(existing_token, str) or payload.rotate_secret:
            extra["callback_token"] = secrets.token_urlsafe(32)
        else:
            extra["callback_token"] = existing_token

    number.webhook_url = str(payload.url)
    number.webhook_events = payload.events
    number.webhook_active = payload.active
    number.webhook_format = payload.format
    number.webhook_extra = extra or None

    await db.commit()
    await db.refresh(number)
    return number, new_secret_plain
