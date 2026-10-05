def message_text(content) -> str:
    """Gemini returns content as a list of blocks; other providers return a string."""
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict))