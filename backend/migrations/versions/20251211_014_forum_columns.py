"""Add missing forum columns

Revision ID: 20251211_014
Revises: 20251210_013
Create Date: 2025-12-11

Adds missing columns to thread and post tables:
- thread: restaurantID (nullable to handle existing data)
- post: datetime
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision = '20251211_014'
down_revision = '20251210_013'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    # Add restaurantID column to thread table
    if not column_exists('thread', 'restaurantID'):
        op.add_column('thread', sa.Column('restaurantID', sa.Integer(), nullable=True))
        
        # Set default restaurant for existing threads (get first restaurant)
        op.execute("""
            UPDATE thread 
            SET "restaurantID" = (SELECT id FROM restaurant LIMIT 1)
            WHERE "restaurantID" IS NULL
        """)
        
        # Add foreign key constraint
        op.create_foreign_key(
            'fk_thread_restaurant',
            'thread', 'restaurant',
            ['restaurantID'], ['id'],
            ondelete='CASCADE'
        )
    
    # Add datetime column to post table
    if not column_exists('post', 'datetime'):
        op.add_column('post', sa.Column('datetime', sa.Text(), nullable=True))
        
        # Set default datetime for existing posts
        op.execute("""
            UPDATE post 
            SET datetime = NOW()::text
            WHERE datetime IS NULL
        """)


def downgrade():
    # Remove datetime column from post
    if column_exists('post', 'datetime'):
        op.drop_column('post', 'datetime')
    
    # Remove restaurantID column and FK from thread
    if column_exists('thread', 'restaurantID'):
        op.drop_constraint('fk_thread_restaurant', 'thread', type_='foreignkey')
        op.drop_column('thread', 'restaurantID')
