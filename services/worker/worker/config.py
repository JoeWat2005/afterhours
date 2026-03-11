from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_ROOT = Path(__file__).resolve().parents[1]


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            REPO_ROOT / ".env",
            REPO_ROOT / ".env.local",
            SERVICE_ROOT / ".env",
            SERVICE_ROOT / ".env.local",
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    environment: str = Field(validation_alias="APP_ENV")
    redis_url: str = Field(validation_alias="WORKER_REDIS_URL")
    api_base_url: str = Field(validation_alias="WORKER_API_BASE_URL")
    notification_batch_size: int = Field(validation_alias="WORKER_NOTIFICATION_BATCH_SIZE")


@lru_cache(maxsize=1)
def get_settings() -> WorkerSettings:
    return WorkerSettings()
