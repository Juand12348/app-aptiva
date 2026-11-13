from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Aptiva AI"
    app_version: str = "0.1.0"
    database_url: str
    cors_origins: list[str] = ["http://localhost:8501"]
    # Sin un secreto largo la app no arranca: un JWT firmado con un secreto débil se puede falsificar.
    jwt_secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=60, gt=0)
    exam_time_limit_minutes: int = Field(default=60, gt=0)
    gemini_api_key: str = Field(min_length=1)
    # Probado el 2026-11-06: 2.5-flash ya no existe para cuentas nuevas; 3.7/3.8-flash daban 503/504 por demanda.
    gemini_model: str = "gemini-3.5-flash"
    gemini_timeout_seconds: int = Field(default=20, gt=0)

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        # Neon entrega "postgresql://", que SQLAlchemy asocia a psycopg2; el proyecto usa psycopg 3.
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
