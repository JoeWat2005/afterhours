from __future__ import annotations

import os
import urllib.parse
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings


REMOVED_TABLES = {
    "heatmap_cells",
    "notification_subscriptions",
    "places",
    "transport_arrivals",
    "transport_services",
    "transport_stops",
}
CORE_TABLES = {"app_users", "journeys", "safety_reports"}


def _scoped_url(base_sync_url: str, schema: str) -> str:
    option = urllib.parse.quote(f"-csearch_path={schema},public")
    joiner = "&" if "?" in base_sync_url else "?"
    return f"{base_sync_url}{joiner}options={option}"


def _alembic_config(url: str) -> Config:
    service_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(service_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(service_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def _table_names(url: str) -> set[str]:
    engine = create_engine(url, future=True)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


@pytest.fixture()
def migration_test_url() -> str:
    base_sync_url = os.getenv("TEST_MIGRATION_DATABASE_URL", "")
    if not base_sync_url.startswith("postgresql+psycopg://"):
        pytest.skip(
            "Set TEST_MIGRATION_DATABASE_URL=postgresql+psycopg://... "
            "to run migration roundtrip integration tests"
        )

    schema = f"test_migration_roundtrip_{uuid4().hex[:10]}"
    admin_engine = create_engine(base_sync_url, future=True)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    try:
        yield _scoped_url(base_sync_url, schema)
    finally:
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin_engine.dispose()


def test_alembic_roundtrip_keeps_core_and_drops_removed_tables(
    migration_test_url: str,
) -> None:
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = migration_test_url
    get_settings.cache_clear()

    cfg = _alembic_config(migration_test_url)
    try:
        command.upgrade(cfg, "head")
        head_tables = _table_names(migration_test_url)
        assert CORE_TABLES.issubset(head_tables)
        assert REMOVED_TABLES.isdisjoint(head_tables)

        command.downgrade(cfg, "97bb2de91084")
        downgraded_tables = _table_names(migration_test_url)
        assert CORE_TABLES.issubset(downgraded_tables)
        assert REMOVED_TABLES.issubset(downgraded_tables)

        command.upgrade(cfg, "head")
        roundtrip_tables = _table_names(migration_test_url)
        assert CORE_TABLES.issubset(roundtrip_tables)
        assert REMOVED_TABLES.isdisjoint(roundtrip_tables)
    finally:
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url
        get_settings.cache_clear()
