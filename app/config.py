from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GEMINI_API_KEY : str
    GEMINI_MODEL : str = "gemini-3.1-flash-lite"
    ALPHA_VANTAGE_API_KEY : str
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    ) 

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()