"""Add dish_images table and order_count column to dishes

Revision ID: 003_dish_images
Revises: 002_add_indices
Create Date: 2025-12-01

Adds:
1. dish_images table for multiple images per dish
2. order_count column to dishes for denormalized popularity tracking
3. Indices for new table and column
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_dish_images'
down_revision: Union[str, None] = '002_add_indices'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =====================================================
    # Add order_count column to dishes for popularity tracking
    # =====================================================
    op.execute("""
        ALTER TABLE dishes 
        ADD COLUMN IF NOT EXISTS order_count INTEGER NOT NULL DEFAULT 0;
    """)
    
    # Index for popularity sorting (order_count descending)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dishes_order_count 
        ON dishes(order_count DESC);
    """)
    
    # Composite index for popularity + rating combined sorting
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dishes_popularity_rating 
        ON dishes(order_count DESC, average_rating DESC);
    """)

    # =====================================================
    # TABLE: dish_images
    # Multiple images for a dish
    # =====================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS dish_images (
            id SERIAL PRIMARY KEY,
            dish_id INTEGER NOT NULL REFERENCES dishes(id) ON DELETE CASCADE,
            image_url TEXT NOT NULL,
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Index for fetching images by dish
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dish_images_dish 
        ON dish_images(dish_id, display_order);
    """)

    # =====================================================
    # Initialize order_count from existing ordered_dishes
    # This updates existing dishes with their actual order counts
    # =====================================================
    op.execute("""
        UPDATE dishes d
        SET order_count = COALESCE(
            (SELECT SUM(od.quantity) 
             FROM ordered_dishes od 
             WHERE od.dish_id = d.id),
            0
        );
    """)


def downgrade() -> None:
    # Drop dish_images table
    op.execute("DROP TABLE IF EXISTS dish_images CASCADE;")
    
    # Drop indices
    op.execute("DROP INDEX IF EXISTS idx_dishes_order_count;")
    op.execute("DROP INDEX IF EXISTS idx_dishes_popularity_rating;")
    
    # Remove order_count column
    op.execute("ALTER TABLE dishes DROP COLUMN IF EXISTS order_count;")
