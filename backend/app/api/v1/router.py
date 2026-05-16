"""Aggregator for all v1 API routes."""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    conversations,
    health,
    integrations,
    media,
    messages,
    numbers,
    settings,
    users,
    webhooks,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(numbers.router)
api_router.include_router(conversations.router)
api_router.include_router(messages.router)
api_router.include_router(webhooks.router)
api_router.include_router(integrations.router)
api_router.include_router(media.router)
api_router.include_router(settings.router)
