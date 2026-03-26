from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

try:
    from app.core.config import settings
except ImportError:
    from app.core.config import settings

# Use the database URL from settings (supports both SQLite and PostgreSQL)
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Convert postgresql:// to postgresql+asyncpg:// for async engine
if SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://"
    )

# For SQLite, we need to enable check_same_thread=False and connect_args
engine_kwargs = {
    "echo": False,  # Set to False in production
    "future": True,
    "pool_pre_ping": True,
    "pool_recycle": 3600,  # Recycle connections every hour
}

# Add SQLite-specific configuration
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL specific optimizations
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 10

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

class Base(DeclarativeBase):
    pass

# ============== SYNC DATABASE ENGINE ==============
# For LangGraph tools that run in separate event loops
# These cannot use async database connections
SYNC_DATABASE_URL = settings.DATABASE_URL
if "postgresql" in SYNC_DATABASE_URL:
    # Replace any async driver with psycopg2
    SYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    SYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")
elif "sqlite+aiosqlite" in SYNC_DATABASE_URL:
    SYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")

sync_engine_kwargs = {"echo": False, "future": True}
if SYNC_DATABASE_URL.startswith("sqlite"):
    sync_engine_kwargs["connect_args"] = {"check_same_thread": False}

sync_engine = create_engine(SYNC_DATABASE_URL, **sync_engine_kwargs)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=False
)

def get_sync_db_session():
    """Get a synchronous database session for use in LangGraph tools."""
    return SyncSessionLocal()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_session_context():
    """
    Async context manager for database sessions.
    Useful for background tasks and scripts where Depends() cannot be used.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
