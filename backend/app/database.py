"""Database connection and session management."""
import logging
import os
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Get database URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/vacation_planner.db")

# Create async engine for SQLite
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=settings.database_echo,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database session (for non-FastAPI contexts)."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully")


async def close_db() -> None:
    """Close database connections."""
    logger.info("Closing database connections...")
    await engine.dispose()
    logger.info("Database connections closed")


async def check_db_connection() -> bool:
    """Check if database connection is healthy."""
    try:
        async with async_session_maker() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
