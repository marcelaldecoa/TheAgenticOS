"""Server configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """AGR server settings — configurable via environment variables."""

    model_config = {"env_prefix": "AGR_"}

    host: str = "0.0.0.0"
    port: int = 8600
    db_path: str = Field(default="agr.db", description="SQLite database path")
    default_tenant: str = "default"
    log_level: str = "info"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    @property
    def db_file(self) -> Path:
        return Path(self.db_path)


settings = Settings()
