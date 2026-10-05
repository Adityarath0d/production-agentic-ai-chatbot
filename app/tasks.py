from app import repository as repo
from app.agent.titles import generate_title
from app.db import SessionLocal
from app.models import DEFAULT_TITLE


async def set_title_if_new(thread_id: str, first_message: str, user_id: str | None = None):
    # 1. Short session: is this chat still untitled?
    async with SessionLocal() as session:
        thread = await repo.get_thread(session, thread_id, user_id)
        if thread is None or thread.title != DEFAULT_TITLE:
            return

    # 2. Slow part, with no database session held open
    title = await generate_title(first_message)

    # 3. Second short session: check again, then save
    async with SessionLocal() as session:
        thread = await repo.get_thread(session, thread_id, user_id)
        if thread is None or thread.title != DEFAULT_TITLE:
            return  # deleted or renamed by the user while the model was thinking
        await repo.rename_thread(session, thread_id, title, user_id)