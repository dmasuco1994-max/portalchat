"""WhatsApp number schemas."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


Status = Literal["created", "connecting", "connected", "disconnected", "failed"]


class WhatsAppNumberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class WhatsAppNumberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    instance_name: str
    phone_number: str | None
    status: Status
    last_connected_at: datetime | None
    created_at: datetime
    updated_at: datetime


class QrCodeResponse(BaseModel):
    """Returned by GET /numbers/{id}/qr while the instance is awaiting pairing."""

    instance_name: str
    status: Status
    qr_base64: str | None = Field(
        default=None,
        description="Base64-encoded PNG of the QR code. Null once paired.",
    )
    pairing_code: str | None = Field(
        default=None,
        description="Alternative 8-digit pairing code (Evolution provides this for some setups).",
    )


class ConnectionStatusResponse(BaseModel):
    instance_name: str
    status: Status
    raw_state: str | None = Field(
        default=None,
        description="Raw connection state reported by Evolution (open/close/connecting).",
    )
