"""Health check endpoint.

Phase 1: shallow health (process is up).
Phase 2+ will add deep health checks (DB ping, Redis ping, Evolution reachable).
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
