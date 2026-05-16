"""WhatsApp number model.

Each row represents one WhatsApp number linked (or linkable) to the platform.
Backed 1:1 by an instance on Evolution API.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


# Connection lifecycle:
#   created      — local row exists, Evolution instance created, not paired
#   connecting   — QR fetched, awaiting scan
#   connected    — paired with a WhatsApp account
#   disconnected — was connected, lost session (network, logout, etc.)
#   failed       — Evolution returned an error during create/connect
VALID_STATUSES = ("created", "connecting", "connected", "disconnected", "failed")
VALID_WEBHOOK_FORMATS = ("portal", "apiwha_neotel")


class WhatsAppNumber(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "whatsapp_numbers"
    __table_args__ = (
        CheckConstraint(
            f"status IN {VALID_STATUSES}",
            name="ck_whatsapp_numbers_status",
        ),
        CheckConstraint(
            f"webhook_format IN {VALID_WEBHOOK_FORMATS}",
            name="ck_whatsapp_numbers_webhook_format",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    instance_name: Mapped[str] = mapped_column(
        String(80), unique=True, nullable=False, index=True
    )
    phone_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="created", index=True
    )
    last_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # CRM webhook configuration (set by tenant via PATCH /numbers/{id}/webhook).
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(128), nullable=True)
    webhook_events: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    webhook_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Delivery format. `portal` = our native JSON envelope + HMAC.
    # `apiwha_neotel` = form-encoded apiwha-compatible POST, no HMAC, for Neotel
    # CAPIWHA-style integrations.
    webhook_format: Mapped[str] = mapped_column(
        String(32), nullable=False, default="portal"
    )
    # Per-format auxiliary config (e.g. apiwha_neotel stores `{"token": "..."}`
    # in case Neotel echoes it back or expects it as a header in some setups).
    webhook_extra: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    organization: Mapped["Organization"] = relationship()  # noqa: F821
