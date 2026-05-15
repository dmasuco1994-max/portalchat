"""WhatsApp number orchestration: keeps our DB in sync with Evolution instances."""
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


def _generate_instance_name() -> str:
    return f"wp_{secrets.token_hex(6)}"


def _webhook_callback_url(instance_name: str) -> str:
    """The URL Evolution should POST to when events fire on this instance."""
    base = settings.public_backend_url.rstrip("/")
    return f"{base}/api/v1/webhooks/evolution/{instance_name}"


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
    """Lookup for the public webhook receiver (no tenant scoping yet)."""
    result = await db.execute(
        select(WhatsAppNumber).where(WhatsAppNumber.instance_name == instance_name)
    )
    return result.scalar_one_or_none()


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

    # Subscribe Evolution to our backend webhook URL so we receive events.
    try:
        await evolution_client.set_webhook(
            number.instance_name,
            url=_webhook_callback_url(number.instance_name),
        )
    except EvolutionAPIError:
        # Webhook config failure is non-fatal at create time — admin can rebind later.
        pass

    await db.commit()
    await db.refresh(number)
    return number


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
    pairing_code = response.get("pairingCode") or response.get("code")

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
    if new_status != number.status:
        number.status = new_status
        if new_status == "connected":
            number.last_connected_at = datetime.now(timezone.utc)
            phone = instance_section.get("owner") or instance_section.get("ownerJid")
            if phone:
                number.phone_number = "".join(ch for ch in phone if ch.isdigit())
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
    """Update CRM webhook config. Returns (number, plain_secret_or_none).

    plain_secret is only returned on initial set or rotation; future GET calls
    will not expose it.
    """
    number = await get_number(db, organization_id, number_id)

    # Clearing config
    if payload.url is None:
        number.webhook_url = None
        number.webhook_events = None
        number.webhook_active = False
        number.webhook_secret = None
        await db.commit()
        await db.refresh(number)
        return number, None

    new_secret_plain: str | None = None
    if number.webhook_secret is None or payload.rotate_secret:
        new_secret_plain = secrets.token_urlsafe(32)
        number.webhook_secret = new_secret_plain

    number.webhook_url = str(payload.url)
    number.webhook_events = payload.events
    number.webhook_active = payload.active

    await db.commit()
    await db.refresh(number)
    return number, new_secret_plain
