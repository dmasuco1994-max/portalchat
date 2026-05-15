"""WhatsApp number orchestration: keeps our DB in sync with Evolution instances."""
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.whatsapp_number import WhatsAppNumber
from app.schemas.whatsapp_number import WhatsAppNumberCreate
from app.services.evolution import (
    EvolutionAPIError,
    evolution_client,
    map_state_to_status,
)


def _generate_instance_name() -> str:
    """Evolution-side identifier. Short, URL-safe, unique."""
    return f"wp_{secrets.token_hex(6)}"


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


async def create_number(
    db: AsyncSession,
    organization_id: UUID,
    payload: WhatsAppNumberCreate,
) -> WhatsAppNumber:
    # Generate a unique instance_name, retry on the (extremely unlikely) collision.
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

    # Create on Evolution. If this fails we roll back our row to avoid orphans.
    try:
        await evolution_client.create_instance(number.instance_name)
    except EvolutionAPIError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Evolution API rejected instance creation: {exc.payload}",
        ) from exc

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

    # Evolution v2 response shape: {"base64": "...", "code": "...", "pairingCode": "..."}
    qr_base64 = response.get("base64") or response.get("qrcode", {}).get("base64")
    pairing_code = response.get("pairingCode") or response.get("code")

    # Bump our status to 'connecting' while we wait for the user to scan.
    if number.status not in ("connected",):
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
    """Ask Evolution for the live state and persist any change to our row."""
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
    changed = new_status != number.status
    if changed:
        number.status = new_status
        if new_status == "connected":
            number.last_connected_at = datetime.now(timezone.utc)
            # Some Evolution versions return the WA number on this endpoint
            phone = instance_section.get("owner") or instance_section.get("ownerJid")
            if phone:
                # JID format "5491134567890@s.whatsapp.net" — keep digits only.
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
        # If Evolution says "instance not connected", that's fine — treat as success.
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
        # If the instance was already gone on Evolution's side, proceed with DB cleanup.
        if exc.status_code not in (400, 404):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Evolution API error: {exc.payload}",
            ) from exc

    await db.delete(number)
    await db.commit()
