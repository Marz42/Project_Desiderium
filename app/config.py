from functools import lru_cache

from pydantic import AliasChoices, Field
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

    youtube_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("YOUTUBE_DATA_API_KEY", "YOUTUBE_API_KEY"),
    )
    youtube_daily_quota_limit: int = Field(default=10_000, alias="YOUTUBE_DAILY_QUOTA_LIMIT")
    youtube_max_search_calls: int = Field(default=100, alias="YOUTUBE_MAX_SEARCH_CALLS")

    crawl_priority_hours: int = Field(default=5, alias="CRAWL_PRIORITY_HOURS")
    crawl_general_hours: int = Field(default=18, alias="CRAWL_GENERAL_HOURS")
    crawl_keyword_hour: int = Field(default=6, alias="CRAWL_KEYWORD_HOUR")

    tiktok_enabled: bool = Field(default=False, alias="TIKTOK_ENABLED")
    tiktok_cookie: str = Field(default="", alias="TIKTOK_COOKIE")
    tiktok_page_version: str = Field(default="v1", alias="TIKTOK_PAGE_VERSION")
    tiktok_crawl_hours: int = Field(default=12, alias="TIKTOK_CRAWL_HOURS")
    tiktok_retry_hours: int = Field(default=2, alias="TIKTOK_RETRY_HOURS")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_model: str = Field(default="", alias="LLM_MODEL")
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    manager_password: str = Field(default="", alias="MANAGER_PASSWORD")

    @property
    def database_url_str(self) -> str:
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
