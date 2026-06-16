"""Application configuration loaded from environment / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://mrsw:mrsw@localhost:5432/mrsw"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60 * 24
    algorithm: str = "HS256"
    cors_origins: str = "*"
    auto_create_tables: bool = True
    seed_on_start: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
