"""Database session management and connection pooling."""
from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_db_engine(database_url: str, echo: bool = False) -> AsyncEngine:
    """Create async SQLAlchemy engine with connection pooling."""
    connect_args = {}
    if "sqlite" in database_url:
        connect_args["check_same_thread"] = False
        return create_async_engine(database_url, echo=echo, connect_args=connect_args)
    
    return create_async_engine(
        database_url,
        echo=echo,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create session maker for async sessions."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def check_db_health(engine: AsyncEngine) -> bool:
    """Execute a simple query to verify database connectivity."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
