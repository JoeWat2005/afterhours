from pathlib import Path

import app.models  # noqa: F401
from app.db.base import Base


def test_core_metadata_only_includes_supported_tables() -> None:
    assert set(Base.metadata.tables.keys()) == {"app_users", "journeys", "safety_reports"}


def test_cleanup_migration_drops_removed_tables() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "a7f0de1d0a1f_remove_unused_prototype_tables.py"
    )
    migration = migration_path.read_text(encoding="utf-8")

    for table in [
        "heatmap_cells",
        "notification_subscriptions",
        "places",
        "transport_arrivals",
        "transport_services",
        "transport_stops",
    ]:
        assert f'op.drop_table("{table}")' in migration

    for table in ["app_users", "journeys", "safety_reports"]:
        assert f'op.drop_table("{table}")' not in migration
