"""Import every model here so Base.metadata sees the full schema."""
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.whatsapp_number import WhatsAppNumber

__all__ = [
    "Conversation",
    "Message",
    "Organization",
    "RefreshToken",
    "User",
    "WhatsAppNumber",
]
