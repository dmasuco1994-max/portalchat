"""User management endpoints (ABM within the current organization)."""
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUser, DbSession, require_admin, require_owner
from app.schemas.user import UserInvite, UserRead, UserUpdate
from app.services.user import (
    delete_user,
    invite_user,
    list_users_in_org,
    update_user,
)


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead, summary="Current authenticated user.")
async def get_me(current: CurrentUser) -> UserRead:
    return UserRead.model_validate(current)


@router.get(
    "",
    response_model=list[UserRead],
    summary="List teammates in the current organization.",
)
async def list_users(db: DbSession, current: CurrentUser) -> list[UserRead]:
    users = await list_users_in_org(db, current.organization_id)
    return [UserRead.model_validate(u) for u in users]


@router.post(
    "/invite",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    summary="Invite a new user to the current organization (admin/owner only).",
)
async def invite(
    payload: UserInvite,
    db: DbSession,
    current: CurrentUser,
) -> UserRead:
    user = await invite_user(db, current.organization_id, payload)
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_admin)],
    summary="Update a user (admin/owner only; role changes restricted to owner).",
)
async def patch_user(
    user_id: UUID,
    payload: UserUpdate,
    db: DbSession,
    current: CurrentUser,
) -> UserRead:
    user = await update_user(
        db, current.organization_id, user_id, payload, actor=current
    )
    return UserRead.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_owner)],
    summary="Delete a user (owner only). Cannot delete self or last owner.",
)
async def remove_user(
    user_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> None:
    await delete_user(db, current.organization_id, user_id, actor=current)
