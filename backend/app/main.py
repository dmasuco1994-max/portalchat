"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import engine

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup hooks (DB pool warmed up implicitly via first query).
    yield
    # Shutdown: dispose of the connection pool cleanly.
    await engine.dispose()


app = FastAPI(
    title="WhatsApp Portal API",
    version="0.2.0",
    description="Multi-tenant WhatsApp gateway portal (Evolution API orchestrator).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "whatsapp-portal",
        "version": "0.2.0",
        "environment": settings.environment,
        "docs": "/docs",
    }
