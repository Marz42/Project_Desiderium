from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "desiderium"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = False
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default="postgresql+asyncpg://desiderium:desiderium@localhost:5432/desiderium",
        alias="DATABASE_URL",
    )

    youtube_api_key: str = Field(default="", alias="YOUTUBE_API_KEY")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")

    @property
    def database_url_str(self) -> str:
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
