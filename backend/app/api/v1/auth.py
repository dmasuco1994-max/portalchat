"""Authentication endpoints: signup, login, refresh, logout."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import LoginRequest, RefreshRequest, SignupRequest, TokenPair
from app.schemas.user import UserRead
from app.services.auth import (
    authenticate_user,
    issue_token_pair,
    revoke_refresh_token,
    rotate_refresh_token,
    signup_organization,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization and its first owner user.",
)
async def signup(payload: SignupRequest, db: DbSession) -> UserRead:
    user = await signup_organization(db, payload)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair, summary="Login with JSON body.")
async def login(payload: LoginRequest, db: DbSession) -> TokenPair:
    user = await authenticate_user(db, payload.email, payload.password)
    access, refresh = await issue_token_pair(db, user)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post(
    "/login/form",
    response_model=TokenPair,
    include_in_schema=False,
    summary="OAuth2-password-form login (used by Swagger's Authorize button).",
)
async def login_form(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> TokenPair:
    user = await authenticate_user(db, form.username, form.password)
    access, refresh = await issue_token_pair(db, user)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Rotate the refresh token, returning a fresh pair.",
)
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    _, access, new_refresh = await rotate_refresh_token(db, payload.refresh_token)
    return TokenPair(access_token=access, refresh_token=new_refresh)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the supplied refresh token.",
)
async def logout(
    payload: RefreshRequest,
    db: DbSession,
    _: CurrentUser,
) -> None:
    await revoke_refresh_token(db, payload.refresh_token)
