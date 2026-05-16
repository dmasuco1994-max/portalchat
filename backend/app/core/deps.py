"""Reusable FastAPI dependencies (DB session, current user, role gates)."""
from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

import jwt
from arq import ArqRedis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal
from app.models.user import User


# tokenUrl points to the form-data login endpoint so Swagger's "Authorize"
# button works out of the box.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/form")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_arq_pool(request: Request) -> ArqRedis:
    return request.app.state.arq_pool


ArqPool = Annotated[ArqRedis, Depends(get_arq_pool)]


async def get_current_user(
    db: DbSession,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise credentials_exc from None

    try:
        user_id = UUID(payload.get("sub", ""))
    except (ValueError, TypeError):
        raise credentials_exc from None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed_roles: str):
    """Factory that builds a dependency enforcing the user's role is allowed."""

    async def _dep(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action",
            )
        return current_user

    return _dep


require_admin = require_role("owner", "admin")
require_owner = require_role("owner")
