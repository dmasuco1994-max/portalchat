"""Auth and signup business logic — talks to DB, returns ORM objects."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import SignupRequest


async def signup_organization(db: AsyncSession, payload: SignupRequest) -> User:
    """Create a new organization with its first owner user atomically."""
    org = Organization(
        name=payload.organization_name,
        slug=payload.organization_slug.lower(),
    )
    db.add(org)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug already taken",
        ) from None

    user = User(
        organization_id=org.id,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="owner",
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


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> User:
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if (
        user is None
        or not user.is_active
        or not verify_password(password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return user


async def issue_token_pair(db: AsyncSession, user: User) -> tuple[str, str]:
    """Issue a fresh (access, refresh) pair and persist refresh hash."""
    access = create_access_token(subject=str(user.id))
    plain_refresh, refresh_hash = generate_refresh_token()

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await db.commit()
    return access, plain_refresh


async def rotate_refresh_token(
    db: AsyncSession, plain_refresh: str
) -> tuple[User, str, str]:
    """Validate a refresh token, revoke it, mint a new pair (rotation pattern)."""
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )
    digest = hash_refresh_token(plain_refresh)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == digest)
    )
    token = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if token is None or token.revoked_at is not None or token.expires_at <= now:
        raise invalid

    user = await db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise invalid

    token.revoked_at = now
    new_access = create_access_token(subject=str(user.id))
    new_plain_refresh, new_refresh_hash = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=new_refresh_hash,
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await db.commit()
    return user, new_access, new_plain_refresh


async def revoke_refresh_token(db: AsyncSession, plain_refresh: str) -> None:
    """Mark a refresh token as revoked (logout). Idempotent."""
    digest = hash_refresh_token(plain_refresh)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == digest)
    )
    token = result.scalar_one_or_none()
    if token is not None and token.revoked_at is None:
        token.revoked_at = datetime.now(timezone.utc)
        await db.commit()
