"""User request/response schemas."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


Role = Literal["owner", "admin", "member"]


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserInvite(BaseModel):
    """Admin/owner invites a user. Phase 2: provisions an initial password to be
    shared out-of-band. Phase 7 will swap to magic-link email invites."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    role: Role = "member"
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    role: Role | None = None
    is_active: bool | None = None
