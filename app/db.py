from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
    

DATABASE_URL = "sqlite+aiosqlite:///app.db"

engine = create_async_engine(DATABASE_URL)

# expire_on_commit=False keeps objects usable after commit; with async
# sessions, lazy reloads after commit fail, so this setting matters.
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass