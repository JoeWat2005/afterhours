from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[4]
SERVICE_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
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

    api_prefix: str = Field(validation_alias="API_PREFIX")
    host: str = Field(validation_alias="HOST")
    port: int = Field(validation_alias="PORT")
    reload: bool = Field(validation_alias="RELOAD")

    environment: str = Field(validation_alias="APP_ENV")
    database_url: str = Field(validation_alias="DATABASE_URL")
    redis_url: str = Field(validation_alias="REDIS_URL")

    clerk_issuer_url: str = Field(
        validation_alias=AliasChoices("CLERK_ISSUER_URL", "CLERK_JWT_ISSUER_DOMAIN"),
    )
    convex_deployment_url: str = Field(validation_alias="CONVEX_DEPLOYMENT_URL")

    route_score_weight_safety: float = Field(validation_alias="ROUTE_SCORE_WEIGHT_SAFETY")
    route_score_weight_speed: float = Field(validation_alias="ROUTE_SCORE_WEIGHT_SPEED")
    route_score_weight_accessibility: float = Field(
        validation_alias="ROUTE_SCORE_WEIGHT_ACCESSIBILITY"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
