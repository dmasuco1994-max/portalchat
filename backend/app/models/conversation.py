"""Conversation = WhatsApp chat thread between one of our numbers and a remote JID."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class Conversation(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint(
            "whatsapp_number_id",
            "remote_jid",
            name="uq_conversations_number_remote",
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
    # Full Baileys JID, e.g. "5491134567890@s.whatsapp.net" or "...@g.us" for groups.
    remote_jid: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    remote_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    remote_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    messages: Mapped[list["Message"]] = relationship(  # noqa: F821
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.sent_at",
    )
