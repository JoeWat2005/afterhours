from pathlib import Path

import pytest
from app.db.base import Base


def test_core_metadata_only_includes_supported_tables() -> None:
    assert set(Base.metadata.tables.keys()) == {"app_users", "journeys", "safety_reports"}


def test_cleanup_migration_drops_removed_tables() -> None:
    versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    migration_files = sorted(versions_dir.glob("*.py"))
    if not migration_files:
        pytest.skip("No migration files found in alembic/versions")
    
    # Use the latest migration file or one that mentions 'remove_unused'
    migration_path = next((f for f in migration_files if "remove_unused" in f.name), migration_files[-1])
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
