"""WhatsApp number schemas."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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
    webhook_url: str | None
    webhook_active: bool
    webhook_events: list[str] | None
    created_at: datetime
    updated_at: datetime


class QrCodeResponse(BaseModel):
    instance_name: str
    status: Status
    qr_base64: str | None = Field(
        default=None,
        description="Base64-encoded PNG of the QR code (data URI). Null once paired.",
    )
    pairing_code: str | None = None


class ConnectionStatusResponse(BaseModel):
    instance_name: str
    status: Status
    raw_state: str | None = None


class WebhookConfigUpdate(BaseModel):
    """Configure the tenant's CRM webhook for this number."""

    url: HttpUrl | None = Field(
        default=None,
        description="CRM webhook URL. Pass null to clear the config.",
    )
    events: list[str] | None = Field(
        default=None,
        description=(
            "Event types to deliver. Common: MESSAGES_UPSERT, MESSAGES_UPDATE, "
            "CONNECTION_UPDATE. Null = deliver everything we support."
        ),
    )
    active: bool = True
    rotate_secret: bool = Field(
        default=False,
        description="If true, generate a new HMAC secret (invalidates any existing one).",
    )


class WebhookConfigResponse(BaseModel):
    """Returned to the tenant after configuring. Includes the secret ONCE; we
    don't return it again on subsequent reads."""

    url: str | None
    events: list[str] | None
    active: bool
    secret: str | None = Field(
        default=None,
        description="HMAC secret. ONLY returned on the response that creates/rotates it.",
    )
