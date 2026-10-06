from dotenv import load_dotenv

load_dotenv()

import json
from contextlib import AsyncExitStack, asynccontextmanager

import httpx
import logfire
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from app import repository as repo
from app.agent.graph import build_graph
from app.db import engine, get_session
from app.routers.threads import router as threads_router
from app.schema import ChatRequest
from app.tasks import set_title_if_new
from app.tools import weather


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        
        checkpointer = await stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string("checkpoints.db")
        )
        
        weather.http_client = await stack.enter_async_context(
            httpx.AsyncClient(timeout=5.0)
        )

        # inside the AsyncExitStack block:
        stack.push_async_callback(engine.dispose)   # closes the DB pool on shutdown
        app.state.graph = build_graph(checkpointer)
        app.state.checkpointer = checkpointer       # needed for delete cleanup
        yield
    # both close automatically here, in reverse order


app = FastAPI(lifespan=lifespan)




logfire.configure()
logfire.instrument_system_metrics()
logfire.instrument_fastapi(app)

app.include_router(threads_router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "graph_exists": hasattr(app.state, "graph") and app.state.graph is not None,
    }

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, session: AsyncSession = Depends(get_session)):
    thread = await repo.get_thread(session, request.thread_id)

    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    await repo.touch_thread(session, request.thread_id)  # Update last_accessed timestamp


    CONFIG = {"configurable": {"thread_id": request.thread_id}}

    async def event_generator():
        async for message_chunk, metadata in app.state.graph.astream(
            {"messages": [("user", request.message)]},
            config=CONFIG,
            stream_mode="messages",
        ):
            # Only forward tokens produced by the model, not tool results
            if metadata.get("langgraph_node") != "agent":
                continue

            content = message_chunk.content

            # Gemini returns content as a list of block dicts, not a plain string
            if isinstance(content, list):
                for block in content:
                    text = block.get("text") if isinstance(block, dict) else None
                    if text:
                        yield f"data: {json.dumps({'content': text})}\n\n"
            elif isinstance(content, str) and content:
                yield f"data: {json.dumps({'content': content})}\n\n"

    return StreamingResponse(
    event_generator(),
    media_type="text/event-stream",
    background=BackgroundTask(
        set_title_if_new, request.thread_id, request.message
    ),
)