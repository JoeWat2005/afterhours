"""merge severity and cleanup migration heads

Revision ID: 0ac2d979d8f4
Revises: 4f5c7a1d2e3b, a7f0de1d0a1f
Create Date: 2026-03-25 21:10:57.853374
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0ac2d979d8f4'
down_revision = ('4f5c7a1d2e3b', 'a7f0de1d0a1f')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass