"""add_delivery_bidding_fields

Revision ID: 20251208_011_delivery_bidding
Revises: 20251206_010_customer_features
Create Date: 2024-12-08

Adds bidding_closes_at to orders and created_at to bids for
bidding deadline and throttle functionality.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251208_011_delivery_bidding'
down_revision = '20251206_010_customer_features'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add bidding_closes_at to orders table
    op.add_column('orders', sa.Column('bidding_closes_at', sa.Text(), nullable=True))
    
    # Add delivered_at to orders table
    op.add_column('orders', sa.Column('delivered_at', sa.Text(), nullable=True))
    
    # Add created_at to bid table for throttling
    op.add_column('bid', sa.Column('created_at', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('bid', 'created_at')
    op.drop_column('orders', 'delivered_at')
    op.drop_column('orders', 'bidding_closes_at')
