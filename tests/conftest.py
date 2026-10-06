import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import models  # noqa: F401  (importing registers the Thread table)
from app.db import Base


@pytest_asyncio.fixture
async def maker(tmp_path):
    """A session factory bound to a fresh, empty database for each test."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_sessionmaker(engine, expire_on_commit=False)

    await engine.dispose()


@pytest_asyncio.fixture
async def session(maker):
    async with maker() as s:
        yield s