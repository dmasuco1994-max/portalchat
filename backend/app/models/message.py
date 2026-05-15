"""Message = one WhatsApp message, inbound or outbound, persisted for history."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


VALID_DIRECTIONS = ("inbound", "outbound")
VALID_CONTENT_TYPES = (
    "text",
    "image",
    "audio",
    "video",
    "document",
    "sticker",
    "location",
    "contact",
    "reaction",
    "unknown",
)
VALID_MESSAGE_STATUSES = (
    "pending",
    "sent",
    "delivered",
    "read",
    "failed",
)


class Message(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint(
            "whatsapp_number_id",
            "evolution_message_id",
            name="uq_messages_number_evolution_id",
        ),
        CheckConstraint(
            f"direction IN {VALID_DIRECTIONS}",
            name="ck_messages_direction",
        ),
        CheckConstraint(
            f"content_type IN {VALID_CONTENT_TYPES}",
            name="ck_messages_content_type",
        ),
        CheckConstraint(
            f"status IN {VALID_MESSAGE_STATUSES}",
            name="ck_messages_status",
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
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    direction: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    evolution_message_id: Mapped[str] = mapped_column(String(120), nullable=False)
    from_jid: Mapped[str] = mapped_column(String(120), nullable=False)
    to_jid: Mapped[str] = mapped_column(String(120), nullable=False)

    content_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="text"
    )
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Full Evolution payload, kept for media handling and debugging.
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Only meaningful for outbound — inbound rows are "delivered" by definition.
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="delivered", index=True
    )

    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")  # noqa: F821
