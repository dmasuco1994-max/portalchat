"""WebhookDelivery — durable record of each outbound CRM webhook attempt.

One row per delivery target. The async worker (`app.workers.arq_worker`) picks
up rows and increments `attempts`, scheduling itself with exponential backoff
until success or `max_attempts` is hit.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


VALID_STATUSES = (
    "pending",      # row created, awaiting first attempt
    "in_progress",  # worker is currently sending
    "success",      # CRM returned 2xx
    "failed",       # last attempt failed but retries remain
    "abandoned",    # exhausted max_attempts; manual intervention needed
)
VALID_FORMATS = ("portal", "apiwha_neotel", "neotel_custom")


class WebhookDelivery(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        CheckConstraint(
            f"status IN {VALID_STATUSES}",
            name="ck_webhook_deliveries_status",
        ),
        CheckConstraint(
            f"format IN {VALID_FORMATS}",
            name="ck_webhook_deliveries_format",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    whatsapp_number_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("whatsapp_numbers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Snapshot of where to send and what — captured at enqueue time so changes
    # to the number's webhook config don't affect already-queued deliveries.
    target_url: Mapped[str] = mapped_column(String(500), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    secret: Mapped[str] = mapped_column(String(128), nullable=False)
    # Wire format for this delivery. Snapshotted at enqueue time so format
    # changes on the number don't affect already-queued deliveries.
    format: Mapped[str] = mapped_column(
        String(32), nullable=False, default="portal"
    )

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )

    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body_excerpt: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
