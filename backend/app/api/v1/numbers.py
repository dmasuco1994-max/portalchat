"""WhatsApp number management endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUser, DbSession, require_admin
from app.schemas.whatsapp_number import (
    ConnectionStatusResponse,
    QrCodeResponse,
    WhatsAppNumberCreate,
    WhatsAppNumberRead,
)
from app.services.whatsapp_number import (
    create_number,
    delete_number,
    disconnect_number,
    fetch_qr,
    list_numbers,
    sync_connection_status,
    get_number,
)


router = APIRouter(prefix="/numbers", tags=["whatsapp-numbers"])


@router.get(
    "",
    response_model=list[WhatsAppNumberRead],
    summary="List WhatsApp numbers in the current organization.",
)
async def list_(db: DbSession, current: CurrentUser) -> list[WhatsAppNumberRead]:
    numbers = await list_numbers(db, current.organization_id)
    return [WhatsAppNumberRead.model_validate(n) for n in numbers]


@router.post(
    "",
    response_model=WhatsAppNumberRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    summary="Provision a new WhatsApp number (creates the Evolution instance).",
)
async def create(
    payload: WhatsAppNumberCreate,
    db: DbSession,
    current: CurrentUser,
) -> WhatsAppNumberRead:
    number = await create_number(db, current.organization_id, payload)
    return WhatsAppNumberRead.model_validate(number)


@router.get(
    "/{number_id}",
    response_model=WhatsAppNumberRead,
    summary="Get one WhatsApp number.",
)
async def get_one(
    number_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> WhatsAppNumberRead:
    number = await get_number(db, current.organization_id, number_id)
    return WhatsAppNumberRead.model_validate(number)


@router.get(
    "/{number_id}/qr",
    response_model=QrCodeResponse,
    dependencies=[Depends(require_admin)],
    summary="Get the QR code (base64 PNG) for pairing this number with WhatsApp.",
)
async def get_qr(
    number_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> QrCodeResponse:
    data = await fetch_qr(db, current.organization_id, number_id)
    return QrCodeResponse(**data)


@router.get(
    "/{number_id}/status",
    response_model=ConnectionStatusResponse,
    summary="Get the live connection status (polls Evolution, updates DB).",
)
async def get_status(
    number_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> ConnectionStatusResponse:
    data = await sync_connection_status(db, current.organization_id, number_id)
    return ConnectionStatusResponse(**data)


@router.post(
    "/{number_id}/disconnect",
    response_model=WhatsAppNumberRead,
    dependencies=[Depends(require_admin)],
    summary="Logout from WhatsApp but keep the instance (re-link later via /qr).",
)
async def disconnect(
    number_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> WhatsAppNumberRead:
    number = await disconnect_number(db, current.organization_id, number_id)
    return WhatsAppNumberRead.model_validate(number)


@router.delete(
    "/{number_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
    summary="Permanently delete this number (removes the Evolution instance too).",
)
async def delete_(
    number_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> None:
    await delete_number(db, current.organization_id, number_id)
