from app import repository as repo
from app import tasks


async def test_sets_title_for_untitled_thread(maker, monkeypatch):
    monkeypatch.setattr(tasks, "SessionLocal", maker)

    async def fake_title(message):
        return "Tokyo Weather"

    monkeypatch.setattr(tasks, "generate_title", fake_title)
    async with maker() as s:
        thread = await repo.create_thread(s)

    await tasks.set_title_if_new(thread.id, "weather in tokyo?")

    async with maker() as s:
        assert (await repo.get_thread(s, thread.id)).title == "Tokyo Weather"


async def test_does_not_overwrite_a_custom_title(maker, monkeypatch):
    monkeypatch.setattr(tasks, "SessionLocal", maker)
    calls = []

    async def fake_title(message):
        calls.append(message)
        return "Generated"

    monkeypatch.setattr(tasks, "generate_title", fake_title)
    async with maker() as s:
        thread = await repo.create_thread(s, title="My own name")

    await tasks.set_title_if_new(thread.id, "hello")

    async with maker() as s:
        assert (await repo.get_thread(s, thread.id)).title == "My own name"
    assert calls == []  # the model was never even called


async def test_does_not_regenerate_once_titled(maker, monkeypatch):
    monkeypatch.setattr(tasks, "SessionLocal", maker)
    titles_to_return = iter(["First title", "Second title"])

    async def fake_title(message):
        return next(titles_to_return)

    monkeypatch.setattr(tasks, "generate_title", fake_title)
    async with maker() as s:
        thread = await repo.create_thread(s)

    await tasks.set_title_if_new(thread.id, "first message")
    await tasks.set_title_if_new(thread.id, "second message")

    async with maker() as s:
        assert (await repo.get_thread(s, thread.id)).title == "First title"


async def test_missing_thread_does_not_crash(maker, monkeypatch):
    monkeypatch.setattr(tasks, "SessionLocal", maker)

    async def fake_title(message):
        return "Whatever"

    monkeypatch.setattr(tasks, "generate_title", fake_title)

    await tasks.set_title_if_new("does-not-exist", "hello")  # must not raise