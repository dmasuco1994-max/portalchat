"""NotificationSettings — per-org channel + alert toggles."""
import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class NotificationSettings(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "notification_settings"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", name="uq_notification_settings_organization"
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Plaintext for v1. Production should swap to a vault-backed reference or
    # at least Fernet-encrypt with SECRET_KEY.
    telegram_bot_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )
    notify_on_number_disconnected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    notify_on_webhook_abandoned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
