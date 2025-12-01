"""Add bidding enhancements: assignment memo and delivery stats

Revision ID: 006_bidding_enhancements
Revises: 005_orders_flow
Create Date: 2025-12-01

This migration adds:
1. assignment_memo column to orders (for storing manager memo when non-lowest bid chosen)
2. Delivery stats columns to DeliveryRating: total_deliveries, on_time_deliveries, avg_delivery_minutes
3. estimated_delivery_minutes column to bids
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006_bidding_enhancements'
down_revision: Union[str, None] = '005_orders_flow'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add assignment_memo to orders table for manager justification when non-lowest bid chosen
    op.execute("""
        ALTER TABLE orders 
        ADD COLUMN IF NOT EXISTS assignment_memo TEXT;
    """)

    # Add delivery stats to DeliveryRating table
    op.execute("""
        ALTER TABLE "DeliveryRating" 
        ADD COLUMN IF NOT EXISTS total_deliveries INTEGER NOT NULL DEFAULT 0;
    """)
    op.execute("""
        ALTER TABLE "DeliveryRating" 
        ADD COLUMN IF NOT EXISTS on_time_deliveries INTEGER NOT NULL DEFAULT 0;
    """)
    op.execute("""
        ALTER TABLE "DeliveryRating" 
        ADD COLUMN IF NOT EXISTS avg_delivery_minutes INTEGER NOT NULL DEFAULT 30;
    """)

    # Add estimated delivery time to bids
    op.execute("""
        ALTER TABLE bid 
        ADD COLUMN IF NOT EXISTS estimated_minutes INTEGER NOT NULL DEFAULT 30;
    """)

    # Create index for faster bid lookups by order
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_bid_order_amount 
        ON bid("orderID", "bidAmount");
    """)


def downgrade() -> None:
    # Remove index
    op.execute("DROP INDEX IF EXISTS idx_bid_order_amount;")

    # Remove columns from bid
    op.execute("ALTER TABLE bid DROP COLUMN IF EXISTS estimated_minutes;")

    # Remove columns from DeliveryRating
    op.execute('ALTER TABLE "DeliveryRating" DROP COLUMN IF EXISTS total_deliveries;')
    op.execute('ALTER TABLE "DeliveryRating" DROP COLUMN IF EXISTS on_time_deliveries;')
    op.execute('ALTER TABLE "DeliveryRating" DROP COLUMN IF EXISTS avg_delivery_minutes;')

    # Remove columns from orders
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS assignment_memo;")
