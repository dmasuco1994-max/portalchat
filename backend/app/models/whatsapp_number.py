"""WhatsApp number model.

Each row represents one WhatsApp number linked (or linkable) to the platform.
Backed 1:1 by an instance on Evolution API.
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
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


class WhatsAppNumber(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "whatsapp_numbers"
    __table_args__ = (
        CheckConstraint(
            f"status IN {VALID_STATUSES}",
            name="ck_whatsapp_numbers_status",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Display label chosen by the user (e.g. "Sales line", "Support EU").
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Evolution-side identifier. Generated server-side; unique across the system
    # because Evolution's namespace is global per server.
    instance_name: Mapped[str] = mapped_column(
        String(80), unique=True, nullable=False, index=True
    )

    # Phone number reported by Evolution after the QR pairing succeeds.
    phone_number: Mapped[str | None] = mapped_column(String(40), nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="created", index=True
    )

    last_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    organization: Mapped["Organization"] = relationship()  # noqa: F821
