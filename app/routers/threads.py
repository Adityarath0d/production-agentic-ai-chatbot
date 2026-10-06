
from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app import repository as repo
from app.db import get_session
from app.schema import ThreadRename
from app.utils import message_text

router = APIRouter(prefix="/threads")

#----------------- API endpoints -----------------
@router.get("")
async def list_threads(session: AsyncSession = Depends(get_session)):
    threads = await repo.list_threads(session)
    return [
        {"id": t.id, "title": t.title, "updated_at": t.updated_at}
        for t in threads
    ]

@router.get("/{thread_id}")
async def get_thread(thread_id: str, session: AsyncSession = Depends(get_session)):
    thread = await repo.get_thread(session, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"id": thread.id, "title": thread.title}


@router.post("", status_code=201)
async def create_thread(session: AsyncSession = Depends(get_session)):
    thread = await repo.create_thread(session)
    return {"id": thread.id, "title": thread.title}


@router.delete("/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    deleted = await repo.delete_thread(session, thread_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Thread not found")

    # TODO: delete the saved messages too, by calling
    #       await request.app.state.checkpointer.adelete_thread(thread_id)
    await request.app.state.checkpointer.adelete_thread(thread_id)



@router.patch("/{thread_id}")
async def rename_thread(thread_id: str, body: ThreadRename, session: AsyncSession = Depends(get_session)):
    thread = await repo.get_thread(session, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    await repo.rename_thread(session, thread_id, body.title)
    return {"id": thread.id, "title": body.title}


@router.get("/{thread_id}/messages")
async def get_messages(
    thread_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    thread = await repo.get_thread(session, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    config = {"configurable": {"thread_id": thread_id}}
    snapshot = await request.app.state.graph.aget_state(config)

    messages = []
    print(snapshot.values)
    for m in snapshot.values.get("messages", []):
        # TODO: if m is a HumanMessage, role = "user"
        #       elif m is an AIMessage, role = "assistant"
        #       else: continue  (tool results)
        if isinstance(m, HumanMessage):
            role = "user"
        elif isinstance(m, AIMessage):
            role = "assistant"
        else:
            continue
        # TODO: text = message_text(m.content)
        text = message_text(m.content)
        # TODO: if text is not empty, append {"role": role, "content": text} to messages
        if text:
            messages.append({"role": role, "content": text})    
    return messages

