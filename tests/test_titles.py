from app.agent import titles


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    def __init__(self, content):
        self.content = content

    async def ainvoke(self, prompt):
        return FakeResponse(self.content)


class BoomLLM:
    async def ainvoke(self, prompt):
        raise RuntimeError("model is down")


def test_fallback_short_message_is_kept():
    assert titles.fallback_title("  hello  ") == "hello"


def test_fallback_long_message_is_cut():
    assert titles.fallback_title("x" * 100) == "x" * 40 + "..."


def test_fallback_empty_message():
    assert titles.fallback_title("   ") == "New chat"


async def test_generate_title_falls_back_when_model_fails(monkeypatch):
    monkeypatch.setattr(titles, "title_llm", BoomLLM())

    title = await titles.generate_title("What's the weather in Tokyo?")

    assert title == "What's the weather in Tokyo?"


async def test_generate_title_strips_quotes(monkeypatch):
    monkeypatch.setattr(titles, "title_llm", FakeLLM(' "Tokyo Weather Check" '))

    assert await titles.generate_title("weather?") == "Tokyo Weather Check"


async def test_generate_title_handles_block_content(monkeypatch):
    blocks = [{"type": "text", "text": "Tokyo Weather"}]
    monkeypatch.setattr(titles, "title_llm", FakeLLM(blocks))

    assert await titles.generate_title("weather?") == "Tokyo Weather"


async def test_generate_title_empty_response_falls_back(monkeypatch):
    monkeypatch.setattr(titles, "title_llm", FakeLLM("   "))

    assert await titles.generate_title("hello there") == "hello there"


async def test_generate_title_is_capped_at_60_chars(monkeypatch):
    monkeypatch.setattr(titles, "title_llm", FakeLLM("a" * 100))

    assert len(await titles.generate_title("x")) == 60