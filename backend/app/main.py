"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from arq.connections import RedisSettings, create_pool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.apiwha_compat import router as apiwha_compat_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import engine

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: open arq pool so the inbound webhook handler can enqueue jobs.
    app.state.arq_pool = await create_pool(
        RedisSettings.from_dsn(settings.redis_url)
    )
    yield
    # Shutdown
    await app.state.arq_pool.close()
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
# rapiwha-compat endpoints live at the root so a CRM with the apiwha host
# hardcoded can swap panel.rapiwha.com → this backend's host with no path
# changes.
app.include_router(apiwha_compat_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "whatsapp-portal",
        "version": "0.2.0",
        "environment": settings.environment,
        "docs": "/docs",
    }
