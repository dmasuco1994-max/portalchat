"""WhatsApp number management endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require_admin
from app.models.webhook_delivery import WebhookDelivery
from app.schemas.webhook_delivery import WebhookDeliveryRead
from app.schemas.whatsapp_number import (
    ConnectionStatusResponse,
    QrCodeResponse,
    WebhookConfigResponse,
    WebhookConfigUpdate,
    WhatsAppNumberCreate,
    WhatsAppNumberRead,
)
from app.services.whatsapp_number import (
    create_number,
    delete_number,
    disconnect_number,
    fetch_qr,
    get_number,
    list_numbers,
    rebind_webhook,
    sync_connection_status,
    update_webhook_config,
)


router = APIRouter(prefix="/numbers", tags=["whatsapp-numbers"])


@router.get("", response_model=list[WhatsAppNumberRead])
async def list_(db: DbSession, current: CurrentUser) -> list[WhatsAppNumberRead]:
    numbers = await list_numbers(db, current.organization_id)
    return [WhatsAppNumberRead.model_validate(n) for n in numbers]


@router.post(
    "",
    response_model=WhatsAppNumberRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create(
    payload: WhatsAppNumberCreate,
    db: DbSession,
    current: CurrentUser,
) -> WhatsAppNumberRead:
    number = await create_number(db, current.organization_id, payload)
    return WhatsAppNumberRead.model_validate(number)


@router.get("/{number_id}", response_model=WhatsAppNumberRead)
async def get_one(
    number_id: UUID, db: DbSession, current: CurrentUser
) -> WhatsAppNumberRead:
    number = await get_number(db, current.organization_id, number_id)
    return WhatsAppNumberRead.model_validate(number)


@router.get(
    "/{number_id}/qr",
    response_model=QrCodeResponse,
    dependencies=[Depends(require_admin)],
)
async def get_qr(
    number_id: UUID, db: DbSession, current: CurrentUser
) -> QrCodeResponse:
    data = await fetch_qr(db, current.organization_id, number_id)
    return QrCodeResponse(**data)


@router.get("/{number_id}/status", response_model=ConnectionStatusResponse)
async def get_status(
    number_id: UUID, db: DbSession, current: CurrentUser
) -> ConnectionStatusResponse:
    data = await sync_connection_status(db, current.organization_id, number_id)
    return ConnectionStatusResponse(**data)


@router.post(
    "/{number_id}/disconnect",
    response_model=WhatsAppNumberRead,
    dependencies=[Depends(require_admin)],
)
async def disconnect(
    number_id: UUID, db: DbSession, current: CurrentUser
) -> WhatsAppNumberRead:
    number = await disconnect_number(db, current.organization_id, number_id)
    return WhatsAppNumberRead.model_validate(number)


@router.delete(
    "/{number_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_(
    number_id: UUID, db: DbSession, current: CurrentUser
) -> None:
    await delete_number(db, current.organization_id, number_id)


@router.get(
    "/{number_id}/webhook-deliveries",
    response_model=list[WebhookDeliveryRead],
    summary="List recent CRM webhook delivery attempts (debugging).",
)
async def list_webhook_deliveries(
    number_id: UUID,
    db: DbSession,
    current: CurrentUser,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[WebhookDeliveryRead]:
    # Tenant scope check via get_number
    await get_number(db, current.organization_id, number_id)
    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.whatsapp_number_id == number_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    return [WebhookDeliveryRead.model_validate(d) for d in result.scalars().all()]


@router.post(
    "/{number_id}/rebind-webhook",
    dependencies=[Depends(require_admin)],
    summary=(
        "Force re-subscription of Evolution to our backend webhook. "
        "Use when the initial subscription on number creation failed (check "
        "backend logs) or after Evolution's data was reset."
    ),
)
async def post_rebind_webhook(
    number_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    return await rebind_webhook(db, current.organization_id, number_id)


@router.patch(
    "/{number_id}/webhook",
    response_model=WebhookConfigResponse,
    dependencies=[Depends(require_admin)],
    summary="Configure the tenant CRM webhook (URL, events, signing secret).",
)
async def patch_webhook(
    number_id: UUID,
    payload: WebhookConfigUpdate,
    db: DbSession,
    current: CurrentUser,
) -> WebhookConfigResponse:
    number, plain_secret = await update_webhook_config(
        db, current.organization_id, number_id, payload
    )
    return WebhookConfigResponse(
        url=number.webhook_url,
        events=number.webhook_events,
        active=number.webhook_active,
        secret=plain_secret,
    )
