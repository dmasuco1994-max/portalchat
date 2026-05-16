"""User management service (CRUD scoped to an organization)."""
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    UserInvite,
    UserSelfUpdate,
    UserUpdate,
)


async def list_users_in_org(
    db: AsyncSession, organization_id: UUID
) -> list[User]:
    result = await db.execute(
        select(User)
        .where(User.organization_id == organization_id)
        .order_by(User.created_at)
    )
    return list(result.scalars().all())


async def invite_user(
    db: AsyncSession,
    organization_id: UUID,
    payload: UserInvite,
) -> User:
    user = User(
        organization_id=organization_id,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from None
    await db.refresh(user)
    return user


async def get_user_in_org(
    db: AsyncSession, organization_id: UUID, user_id: UUID
) -> User:
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


async def _count_active_owners(db: AsyncSession, organization_id: UUID) -> int:
    result = await db.execute(
        select(User).where(
            User.organization_id == organization_id,
            User.role == "owner",
            User.is_active.is_(True),
        )
    )
    return len(list(result.scalars().all()))


async def update_user(
    db: AsyncSession,
    organization_id: UUID,
    user_id: UUID,
    payload: UserUpdate,
    actor: User,
) -> User:
    user = await get_user_in_org(db, organization_id, user_id)

    # Role change: only owner can promote/demote; cannot demote last owner.
    if payload.role is not None and payload.role != user.role:
        if actor.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can change roles",
            )
        if user.role == "owner" and payload.role != "owner":
            if await _count_active_owners(db, organization_id) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote the last active owner",
                )
        user.role = payload.role

    if payload.full_name is not None:
        user.full_name = payload.full_name

    if payload.is_active is not None and payload.is_active != user.is_active:
        # Cannot deactivate the last active owner.
        if not payload.is_active and user.role == "owner":
            if await _count_active_owners(db, organization_id) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the last active owner",
                )
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)
    return user


async def update_self(
    db: AsyncSession,
    actor: User,
    payload: UserSelfUpdate,
) -> User:
    """Self-service profile update. Cannot change own role or active flag
    here — those are admin actions via /users/{id}."""
    if payload.full_name is not None:
        actor.full_name = payload.full_name
    await db.commit()
    await db.refresh(actor)
    return actor


async def change_self_password(
    db: AsyncSession,
    actor: User,
    payload: ChangePasswordRequest,
) -> None:
    """Change own password. Requires the current password as proof."""
    if not verify_password(payload.current_password, actor.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no coincide",
        )
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña nueva tiene que ser distinta",
        )
    actor.password_hash = hash_password(payload.new_password)
    await db.commit()


async def delete_user(
    db: AsyncSession,
    organization_id: UUID,
    user_id: UUID,
    actor: User,
) -> None:
    user = await get_user_in_org(db, organization_id, user_id)
    if user.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use deactivate or transfer ownership rather than deleting yourself",
        )
    if user.role == "owner" and await _count_active_owners(db, organization_id) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last active owner",
        )
    await db.delete(user)
    await db.commit()
