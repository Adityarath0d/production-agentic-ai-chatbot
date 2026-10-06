import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app import repository as repo
from app.db import get_session
from app.routers.threads import router


class FakeCheckpointer:
    def __init__(self):
        self.deleted = []

    async def adelete_thread(self, thread_id):
        self.deleted.append(thread_id)


class FakeSnapshot:
    def __init__(self, values):
        self.values = values


class FakeGraph:
    def __init__(self, messages=None):
        self.messages = messages or []

    async def aget_state(self, config):
        return FakeSnapshot({"messages": self.messages} if self.messages else {})


@pytest.fixture
def app(maker):
    test_app = FastAPI()
    test_app.include_router(router)

    async def override_get_session():
        async with maker() as s:
            yield s

    test_app.dependency_overrides[get_session] = override_get_session
    test_app.state.checkpointer = FakeCheckpointer()
    test_app.state.graph = FakeGraph()
    return test_app


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_create_and_list(client):
    r = await client.post("/threads")
    assert r.status_code == 201
    created = r.json()
    assert created["title"] == "New chat"

    r = await client.get("/threads")
    assert r.status_code == 200
    assert [t["id"] for t in r.json()] == [created["id"]]


async def test_get_thread(client):
    created = (await client.post("/threads")).json()

    r = await client.get(f"/threads/{created['id']}")

    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


async def test_get_missing_thread_is_404(client):
    r = await client.get("/threads/does-not-exist")
    assert r.status_code == 404


async def test_rename(client):
    created = (await client.post("/threads")).json()

    r = await client.patch(f"/threads/{created['id']}", json={"title": "Goa trip"})

    assert r.status_code == 200
    assert r.json()["title"] == "Goa trip"
    listing = (await client.get("/threads")).json()
    assert listing[0]["title"] == "Goa trip"


async def test_rename_rejects_empty_title(client):
    created = (await client.post("/threads")).json()

    r = await client.patch(f"/threads/{created['id']}", json={"title": ""})

    assert r.status_code == 422


async def test_rename_missing_is_404(client):
    r = await client.patch("/threads/does-not-exist", json={"title": "x"})
    assert r.status_code == 404


async def test_delete_cleans_up_messages(client, app):
    created = (await client.post("/threads")).json()

    r = await client.delete(f"/threads/{created['id']}")

    assert r.status_code == 204
    assert (await client.get(f"/threads/{created['id']}")).status_code == 404
    assert app.state.checkpointer.deleted == [created["id"]]


async def test_delete_missing_is_404_and_skips_cleanup(client, app):
    r = await client.delete("/threads/does-not-exist")

    assert r.status_code == 404
    assert app.state.checkpointer.deleted == []


async def test_endpoints_hide_other_users_threads(client, app, maker):
    # The endpoints currently act as the anonymous user (user_id=None),
    # so a thread owned by "user-a" must be invisible to every one of them.
    async with maker() as s:
        other = await repo.create_thread(s, user_id="user-a", title="Private")
    thread_id = other.id

    assert (await client.get("/threads")).json() == []
    assert (await client.get(f"/threads/{thread_id}")).status_code == 404
    assert (await client.get(f"/threads/{thread_id}/messages")).status_code == 404
    patch = await client.patch(f"/threads/{thread_id}", json={"title": "Hacked"})
    assert patch.status_code == 404
    assert (await client.delete(f"/threads/{thread_id}")).status_code == 404

    # The failed delete must not have touched the saved messages either
    assert app.state.checkpointer.deleted == []

    async with maker() as s:
        still_there = await repo.get_thread(s, thread_id, user_id="user-a")
    assert still_there is not None
    assert still_there.title == "Private"


async def test_messages_filters_tool_noise(client, app):
    created = (await client.post("/threads")).json()
    app.state.graph = FakeGraph(
        [
            HumanMessage(content="weather in Tokyo?"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "get_weather", "args": {"city": "Tokyo"}, "id": "call_1"}
                ],
            ),
            ToolMessage(content="Tokyo: sunny", tool_call_id="call_1"),
            AIMessage(content=[{"type": "text", "text": "It's sunny in Tokyo."}]),
        ]
    )

    r = await client.get(f"/threads/{created['id']}/messages")

    assert r.status_code == 200
    assert r.json() == [
        {"role": "user", "content": "weather in Tokyo?"},
        {"role": "assistant", "content": "It's sunny in Tokyo."},
    ]


async def test_messages_empty_thread(client):
    created = (await client.post("/threads")).json()

    r = await client.get(f"/threads/{created['id']}/messages")

    assert r.status_code == 200
    assert r.json() == []