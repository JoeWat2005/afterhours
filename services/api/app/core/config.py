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
        extra="ignore",
    )

    api_prefix: str = Field(default="/v1", validation_alias="API_PREFIX")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    reload: bool = Field(default=False, validation_alias="RELOAD")

    environment: str = Field(default="development", validation_alias="APP_ENV")
    database_url: str = Field(
        default="postgresql+psycopg://afterhours:afterhours@localhost:5432/afterhours",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")

    clerk_issuer_url: str = Field(
        default="https://example.clerk.accounts.dev",
        validation_alias=AliasChoices("CLERK_ISSUER_URL", "CLERK_JWT_ISSUER_DOMAIN"),
    )
    convex_deployment_url: str = Field(
        default="https://example.convex.cloud",
        validation_alias="CONVEX_DEPLOYMENT_URL",
    )

    route_score_weight_safety: float = Field(
        default=0.30,
        ge=0,
        validation_alias="ROUTE_SCORE_WEIGHT_SAFETY",
    )
    route_score_weight_lighting: float = Field(
        default=0.20,
        ge=0,
        validation_alias="ROUTE_SCORE_WEIGHT_LIGHTING",
    )
    route_score_weight_accessibility: float = Field(
        default=0.20,
        ge=0,
        validation_alias="ROUTE_SCORE_WEIGHT_ACCESSIBILITY",
    )
    route_score_weight_transport: float = Field(
        default=0.10,
        ge=0,
        validation_alias="ROUTE_SCORE_WEIGHT_TRANSPORT",
    )
    route_score_weight_efficiency: float = Field(
        default=0.10,
        ge=0,
        validation_alias=AliasChoices("ROUTE_SCORE_WEIGHT_EFFICIENCY", "ROUTE_SCORE_WEIGHT_SPEED"),
    )
    route_score_weight_amenity: float = Field(
        default=0.10,
        ge=0,
        validation_alias="ROUTE_SCORE_WEIGHT_AMENITY",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
