"""Message schemas."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


Direction = Literal["inbound", "outbound"]
ContentType = Literal[
    "text", "image", "audio", "video", "document",
    "sticker", "location", "contact", "reaction", "unknown",
]
MessageStatus = Literal["pending", "sent", "delivered", "read", "failed"]


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    whatsapp_number_id: UUID
    direction: Direction
    evolution_message_id: str
    from_jid: str
    to_jid: str
    content_type: ContentType
    content_text: str | None
    media_url: str | None
    status: MessageStatus
    sent_at: datetime
    created_at: datetime


class SendTextRequest(BaseModel):
    """Send a text message via this number."""

    to: str = Field(
        min_length=5,
        max_length=40,
        description=(
            "Recipient phone number including country code, digits only "
            "(e.g. '5491134567890'). The @s.whatsapp.net suffix is added automatically."
        ),
        pattern=r"^\d+$",
    )
    text: str = Field(min_length=1, max_length=4096)
