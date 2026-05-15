"""Aggregator for all v1 API routes."""
from fastapi import APIRouter

from app.api.v1 import auth, health, numbers, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(numbers.router)
