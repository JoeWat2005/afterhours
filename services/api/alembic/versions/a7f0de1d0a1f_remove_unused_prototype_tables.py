"""remove unused prototype tables

Revision ID: a7f0de1d0a1f
Revises: 97bb2de91084
Create Date: 2026-03-25 14:10:00.000000
"""

from alembic import op
import geoalchemy2
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a7f0de1d0a1f"
down_revision = "97bb2de91084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("transport_arrivals")
    op.drop_table("notification_subscriptions")
    op.drop_table("transport_stops")
    op.drop_table("transport_services")
    op.drop_table("places")
    op.drop_table("heatmap_cells")


def downgrade() -> None:
    op.create_table(
        "heatmap_cells",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "cell_geometry",
            geoalchemy2.types.Geometry(
                geometry_type="POLYGON",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "places",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.Column("is_open_late", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "transport_services",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("service_name", sa.String(length=128), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("operator_name", sa.String(length=128), nullable=True),
        sa.Column("active_hours", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "transport_stops",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("stop_code", sa.String(length=64), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stop_code"),
    )

    op.create_table(
        "notification_subscriptions",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("config", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "transport_arrivals",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("stop_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("service_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("expected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["transport_services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stop_id"], ["transport_stops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
