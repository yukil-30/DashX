"""Add is_specialty column to dishes table

Revision ID: 20251211_019
Revises: 20251211_018
Create Date: 2025-12-11

Adds is_specialty boolean column to dishes table for VIP-exclusive specialty dishes.
Non-VIP customers cannot order dishes marked as specialty.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251211_019'
down_revision = '20251211_018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_specialty column with default False
    op.add_column('dishes', sa.Column('is_specialty', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('dishes', 'is_specialty')
