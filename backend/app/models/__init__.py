"""Import every model here so Base.metadata sees the full schema.

Alembic --autogenerate inspects Base.metadata, so any model not imported in this
module will be invisible to migrations.
"""
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.whatsapp_number import WhatsAppNumber

__all__ = ["Organization", "RefreshToken", "User", "WhatsAppNumber"]
