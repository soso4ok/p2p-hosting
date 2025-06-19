import os
from typing import Any, AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

# Test
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/p2p_db"
)

engine = create_async_engine(DATABASE_URL, future=True)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[Any, Any]:
    async with AsyncSessionLocal() as session:
        yield session


async def test_db_connection():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
