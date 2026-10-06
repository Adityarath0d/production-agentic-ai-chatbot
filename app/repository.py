# app/repository.py
import uuid

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DEFAULT_TITLE, Thread, utcnow


def _owned_by(user_id: str | None) -> ColumnElement[bool]:
    """Filter: threads belonging to this user. None means 'no owner yet'."""
    if user_id is None:
        return Thread.user_id.is_(None)
    return Thread.user_id == user_id


async def create_thread(
    session: AsyncSession, user_id: str | None = None, title: str = DEFAULT_TITLE
) -> Thread:
    thread = Thread(id=str(uuid.uuid4()), title=title, user_id=user_id)
    session.add(thread)
    await session.commit()
    return thread


async def list_threads(
    session: AsyncSession, user_id: str | None = None, include_archived: bool = False
) -> list[Thread]:
    stmt = select(Thread).where(_owned_by(user_id))
    if not include_archived:
        stmt = stmt.where(Thread.archived.is_(False))
    stmt = stmt.order_by(Thread.updated_at.desc())

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_thread(
    session: AsyncSession, thread_id: str, user_id: str | None = None
) -> Thread | None:
    stmt = select(Thread).where(Thread.id == thread_id, _owned_by(user_id))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def rename_thread(
    session: AsyncSession, thread_id: str, title: str, user_id: str | None = None
) -> Thread | None:
    thread = await get_thread(session, thread_id, user_id)
    if thread is None:
        return None
    thread.title = title
    await session.commit()
    return thread


async def touch_thread(
    session: AsyncSession, thread_id: str, user_id: str | None = None
) -> None:
    thread = await get_thread(session, thread_id, user_id)
    if thread is None:
        return
    thread.updated_at = utcnow()
    await session.commit()


async def delete_thread(
    session: AsyncSession, thread_id: str, user_id: str | None = None
) -> bool:
    thread = await get_thread(session, thread_id, user_id)
    if thread is None:
        return False
    await session.delete(thread)
    await session.commit()
    return True