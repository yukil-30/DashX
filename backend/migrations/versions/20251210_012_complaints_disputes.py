"""Complaints & Disputes Enhancement

Revision ID: 20251210_012
Revises: 20251206_010
Create Date: 2025-12-10

Adds:
- disputed field to complaint table for dispute tracking
- dispute_reason field for dispute explanation
- disputed_at timestamp
- target_type field to track role of person complained about
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers
revision = '20251210_012'
down_revision = '20251206_010'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name, index_name):
    """Check if an index exists"""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade():
    # Add dispute-related columns to complaint table (if they don't exist)
    if not column_exists('complaint', 'disputed'):
        op.add_column('complaint', sa.Column('disputed', sa.Boolean(), nullable=False, server_default='false'))
    if not column_exists('complaint', 'dispute_reason'):
        op.add_column('complaint', sa.Column('dispute_reason', sa.Text(), nullable=True))
    if not column_exists('complaint', 'disputed_at'):
        op.add_column('complaint', sa.Column('disputed_at', sa.Text(), nullable=True))
    if not column_exists('complaint', 'target_type'):
        op.add_column('complaint', sa.Column('target_type', sa.String(50), nullable=True))
    
    # Create indexes (if they don't exist)
    if not index_exists('complaint', 'idx_complaint_disputed'):
        op.create_index('idx_complaint_disputed', 'complaint', ['disputed'], postgresql_where=sa.text('disputed = true'))
    if not index_exists('complaint', 'idx_complaint_status'):
        op.create_index('idx_complaint_status', 'complaint', ['status'])


def downgrade():
    op.drop_index('idx_complaint_status', table_name='complaint')
    op.drop_index('idx_complaint_disputed', table_name='complaint')
    op.drop_column('complaint', 'target_type')
    op.drop_column('complaint', 'disputed_at')
    op.drop_column('complaint', 'dispute_reason')
    op.drop_column('complaint', 'disputed')
