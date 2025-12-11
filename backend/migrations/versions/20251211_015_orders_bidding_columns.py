"""Add bidding_closes_at and delivered_at columns to orders

Revision ID: 015_orders_bidding_columns
Revises: 20251211_014_forum_columns
Create Date: 2025-12-11

This migration adds:
1. bidding_closes_at column to orders table (ISO timestamp when bidding closes)
2. delivered_at column to orders table (ISO timestamp when order was delivered)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20251211_015'
down_revision: Union[str, None] = '20251211_014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add bidding_closes_at column to orders table
    op.execute("""
        ALTER TABLE orders 
        ADD COLUMN IF NOT EXISTS bidding_closes_at TEXT;
    """)
    
    # Add delivered_at column to orders table
    op.execute("""
        ALTER TABLE orders 
        ADD COLUMN IF NOT EXISTS delivered_at TEXT;
    """)


def downgrade() -> None:
    # Remove the columns if rolling back
    op.execute("""
        ALTER TABLE orders 
        DROP COLUMN IF EXISTS bidding_closes_at;
    """)
    op.execute("""
        ALTER TABLE orders 
        DROP COLUMN IF EXISTS delivered_at;
    """)
