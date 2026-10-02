from dotenv import load_dotenv

from app import deps
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager, AsyncExitStack
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.agent.graph import build_graph
from app.schema import ChatRequest
from app.tools import weather

from app.db import engine
from app.routers.threads import router as threads_router

import logfire
import json
import httpx

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


@app.post("/chat")
async def chat(request: ChatRequest):
    CONFIG = {"configurable": {"thread_id": request.thread_id}}

    response = await app.state.graph.ainvoke(
        {"messages": [("user", request.message)]}, config=CONFIG
    )

    return {"response": response["messages"][-1].content[0]["text"]}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
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

    return StreamingResponse(event_generator(), media_type="text/event-stream")