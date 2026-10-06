from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.utils import message_text

title_llm = ChatGoogleGenerativeAI(
    model=settings.GEMINI_MODEL, api_key=settings.GEMINI_API_KEY
)

PROMPT = (
    "Write a title of at most 5 words for a chat that starts with the message below. "
    "Reply with the title only, no quotes, no punctuation at the end.\n\n"
    "Message: {message}"
)


def fallback_title(message: str) -> str:
    text = message.strip()
    if not text:
        return "New chat"
    if len(text) <= 40:
        return text
    return text[:40].rstrip() + "..."


async def generate_title(message: str) -> str:
    try:
        response = await title_llm.ainvoke(PROMPT.format(message=message[:500]))
        title = message_text(response.content).strip().strip("\"'").strip()
        if not title:
            return fallback_title(message)
        return title[:60]
    except Exception: # noqa: BLE001 - titles are optional, so any failure falls back
        # Titles are optional. Any failure falls back, and chat never breaks.
        return fallback_title(message)