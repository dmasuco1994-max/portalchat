"""Async SQLAlchemy engine and session factory."""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    # pool_pre_ping=True breaks under asyncpg in some reload scenarios
    # (MissingGreenlet on ping). Re-enable in production with proper config.
    pool_pre_ping=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
