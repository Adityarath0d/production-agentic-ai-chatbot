import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

http_client: httpx.AsyncClient | None = None  # set by lifespan at startup


class WeatherInput(BaseModel):
    city: str = Field(description="The city name, e.g. 'Tokyo' or 'Indore'")


@tool("get_weather", args_schema=WeatherInput)
async def get_weather(city: str) -> str:
    """Get the current weather conditions for a given city."""
    try:
        resp = await http_client.get(f"https://wttr.in/{city}", params={"format": "3"})
        resp.raise_for_status()
        return resp.text.strip()
    except httpx.HTTPError as e:
        return f"Couldn't fetch weather for {city}: {e}"