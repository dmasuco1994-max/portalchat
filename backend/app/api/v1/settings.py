"""Org-level settings endpoints: notifications + workspace."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require_admin, require_owner
from app.models.organization import Organization
from app.schemas.notifications import (
    NotificationSettingsRead,
    NotificationSettingsUpdate,
    TelegramTestResult,
)
from app.services import notifications as notifications_service


router = APIRouter(prefix="/settings", tags=["settings"])


def _to_read(row) -> NotificationSettingsRead:
    return NotificationSettingsRead(
        telegram_chat_id=row.telegram_chat_id,
        notify_on_number_disconnected=row.notify_on_number_disconnected,
        notify_on_webhook_abandoned=row.notify_on_webhook_abandoned,
        has_telegram_bot_token=bool(row.telegram_bot_token),
        telegram_bot_token_hint=notifications_service.hint_for_token(
            row.telegram_bot_token
        ),
    )


@router.get("/notifications", response_model=NotificationSettingsRead)
async def get_notifications(
    db: DbSession, current: CurrentUser
) -> NotificationSettingsRead:
    row = await notifications_service.get_or_create_settings(
        db, current.organization_id
    )
    return _to_read(row)


@router.patch(
    "/notifications",
    response_model=NotificationSettingsRead,
    dependencies=[Depends(require_admin)],
)
async def patch_notifications(
    payload: NotificationSettingsUpdate,
    db: DbSession,
    current: CurrentUser,
) -> NotificationSettingsRead:
    row = await notifications_service.update_settings(
        db, current.organization_id, payload
    )
    return _to_read(row)


@router.post(
    "/notifications/test",
    response_model=TelegramTestResult,
    dependencies=[Depends(require_admin)],
    summary="Send a synthetic Telegram message using the saved bot+chat to "
    "verify the configuration end-to-end.",
)
async def post_notifications_test(
    db: DbSession, current: CurrentUser
) -> TelegramTestResult:
    row = await notifications_service.get_or_create_settings(
        db, current.organization_id
    )
    ok, detail = await notifications_service.send_test_message(row)
    return TelegramTestResult(success=ok, detail=detail)


# ---- Workspace --------------------------------------------------------
class WorkspaceRead(BaseModel):
    id: str
    name: str
    slug: str


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


@router.get("/workspace", response_model=WorkspaceRead)
async def get_workspace(
    db: DbSession, current: CurrentUser
) -> WorkspaceRead:
    result = await db.execute(
        select(Organization).where(Organization.id == current.organization_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )
    return WorkspaceRead(id=str(org.id), name=org.name, slug=org.slug)


@router.patch(
    "/workspace",
    response_model=WorkspaceRead,
    dependencies=[Depends(require_owner)],
    summary="Rename the workspace. Only owners. Slug stays immutable for now "
    "(changing it would break any cached integration URLs).",
)
async def patch_workspace(
    payload: WorkspaceUpdate,
    db: DbSession,
    current: CurrentUser,
) -> WorkspaceRead:
    result = await db.execute(
        select(Organization).where(Organization.id == current.organization_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )
    org.name = payload.name.strip()
    await db.commit()
    await db.refresh(org)
    return WorkspaceRead(id=str(org.id), name=org.name, slug=org.slug)
