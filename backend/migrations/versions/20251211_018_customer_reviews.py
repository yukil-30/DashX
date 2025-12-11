"""Add customer_reviews table for delivery driver reviews of customers

Revision ID: 20251211_018
Revises: 20251210_017
Create Date: 2025-12-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251211_018'
down_revision = '20251210_017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create customer_reviews table
    op.execute("""
        CREATE TABLE IF NOT EXISTS customer_reviews (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE UNIQUE,
            customer_id INTEGER NOT NULL REFERENCES accounts("ID") ON DELETE CASCADE,
            reviewer_id INTEGER NOT NULL REFERENCES accounts("ID") ON DELETE CASCADE,
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            review_text TEXT,
            was_polite BOOLEAN,
            easy_to_find BOOLEAN,
            created_at TEXT NOT NULL
        );
    """)
    
    # Add indices for common queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_customer_reviews_customer_id ON customer_reviews(customer_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_customer_reviews_reviewer_id ON customer_reviews(reviewer_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_customer_reviews_order_id ON customer_reviews(order_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS customer_reviews CASCADE;")
