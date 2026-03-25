"""add severity to safety reports

Revision ID: 4f5c7a1d2e3b
Revises: 97bb2de91084
Create Date: 2026-03-24 12:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4f5c7a1d2e3b"
down_revision = "97bb2de91084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "safety_reports",
        sa.Column("severity", sa.String(length=16), nullable=True),
    )

    op.execute(
        """
        UPDATE safety_reports
        SET severity = CASE lower(category)
            WHEN 'assault' THEN 'critical'
            WHEN 'robbery' THEN 'critical'
            WHEN 'harassment' THEN 'high'
            WHEN 'theft' THEN 'medium'
            WHEN 'suspicious activity' THEN 'medium'
            WHEN 'unsafe crossing' THEN 'medium'
            WHEN 'poor lighting' THEN 'low'
            WHEN 'hazard' THEN 'low'
            WHEN 'other' THEN 'low'
            ELSE 'low'
        END
        """
    )

    op.alter_column("safety_reports", "severity", nullable=False)


def downgrade() -> None:
    op.drop_column("safety_reports", "severity")
