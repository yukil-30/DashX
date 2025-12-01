"""Add ordering flow fields and transactions table

Revision ID: 005_orders_flow
Revises: 004_authoritative_schema
Create Date: 2025-12-01

This migration adds:
1. New columns to accounts: free_delivery_credits, completed_orders_count
2. New columns to orders: delivery_address, delivery_fee, subtotal_cents, discount_cents, free_delivery_used
3. New table: transactions (for audit logging of balance changes)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005_orders_flow'
down_revision: Union[str, None] = '004_authoritative_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to accounts table
    op.execute("""
        ALTER TABLE accounts 
        ADD COLUMN IF NOT EXISTS free_delivery_credits INTEGER NOT NULL DEFAULT 0;
    """)
    op.execute("""
        ALTER TABLE accounts 
        ADD COLUMN IF NOT EXISTS completed_orders_count INTEGER NOT NULL DEFAULT 0;
    """)

    # Add new columns to orders table
    op.execute("""
        ALTER TABLE orders 
        ADD COLUMN IF NOT EXISTS delivery_address TEXT;
    """)
    op.execute("""
        ALTER TABLE orders 
        ADD COLUMN IF NOT EXISTS delivery_fee INTEGER NOT NULL DEFAULT 0;
    """)
    op.execute("""
        ALTER TABLE orders 
        ADD COLUMN IF NOT EXISTS subtotal_cents INTEGER NOT NULL DEFAULT 0;
    """)
    op.execute("""
        ALTER TABLE orders 
        ADD COLUMN IF NOT EXISTS discount_cents INTEGER NOT NULL DEFAULT 0;
    """)
    op.execute("""
        ALTER TABLE orders 
        ADD COLUMN IF NOT EXISTS free_delivery_used INTEGER NOT NULL DEFAULT 0;
    """)

    # Create transactions table for audit logging
    op.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            "accountID" INTEGER NOT NULL REFERENCES accounts("ID") ON DELETE CASCADE,
            amount_cents INTEGER NOT NULL,
            balance_before INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            transaction_type VARCHAR(50) NOT NULL,
            reference_type VARCHAR(50),
            reference_id INTEGER,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create index on transactions for faster lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_account 
        ON transactions("accountID");
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_reference 
        ON transactions(reference_type, reference_id);
    """)


def downgrade() -> None:
    # Drop transactions table
    op.execute("DROP TABLE IF EXISTS transactions CASCADE;")

    # Remove columns from orders table
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS delivery_address;")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS delivery_fee;")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS subtotal_cents;")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS discount_cents;")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS free_delivery_used;")

    # Remove columns from accounts table
    op.execute("ALTER TABLE accounts DROP COLUMN IF EXISTS free_delivery_credits;")
    op.execute("ALTER TABLE accounts DROP COLUMN IF EXISTS completed_orders_count;")
