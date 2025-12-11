"""Add created_at column to bid table

Revision ID: 016_bid_created_at
Revises: 20251211_015
Create Date: 2025-12-11

This migration adds:
1. created_at column to bid table for bid throttling (ISO timestamp)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20251211_016'
down_revision: Union[str, None] = '20251211_015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add created_at column to bid table for throttling
    op.execute("""
        ALTER TABLE bid 
        ADD COLUMN IF NOT EXISTS created_at TEXT;
    """)


def downgrade() -> None:
    # Remove the column if rolling back
    op.execute("""
        ALTER TABLE bid 
        DROP COLUMN IF EXISTS created_at;
    """)
