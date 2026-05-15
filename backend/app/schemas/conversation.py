"""Conversation schemas."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    whatsapp_number_id: UUID
    remote_jid: str
    remote_phone: str | None
    remote_name: str | None
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime
