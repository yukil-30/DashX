"""Add reputation system fields

Revision ID: 20251210_013
Revises: 20251210_012
Create Date: 2025-12-10

Adds reputation tracking fields to accounts table:
- Employee: rolling_avg_rating, total_rating_count, complaint_count, compliment_count, 
           demotion_count, employment_status, bonus_count, last_bonus_at
- Customer: customer_tier, dispute_status
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import NUMERIC


# revision identifiers
revision = '20251210_013'
down_revision = '20251210_012'
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
    # Add reputation fields to accounts table (if they don't exist)
    
    # Employee reputation tracking
    if not column_exists('accounts', 'rolling_avg_rating'):
        op.add_column('accounts', sa.Column('rolling_avg_rating', NUMERIC(3, 2), nullable=True, server_default='0.00'))
    
    if not column_exists('accounts', 'total_rating_count'):
        op.add_column('accounts', sa.Column('total_rating_count', sa.Integer(), nullable=False, server_default='0'))
    
    if not column_exists('accounts', 'complaint_count'):
        op.add_column('accounts', sa.Column('complaint_count', sa.Integer(), nullable=False, server_default='0'))
    
    if not column_exists('accounts', 'compliment_count'):
        op.add_column('accounts', sa.Column('compliment_count', sa.Integer(), nullable=False, server_default='0'))
    
    if not column_exists('accounts', 'demotion_count'):
        op.add_column('accounts', sa.Column('demotion_count', sa.Integer(), nullable=False, server_default='0'))
    
    if not column_exists('accounts', 'employment_status'):
        op.add_column('accounts', sa.Column('employment_status', sa.String(50), nullable=False, server_default='active'))
    
    if not column_exists('accounts', 'bonus_count'):
        op.add_column('accounts', sa.Column('bonus_count', sa.Integer(), nullable=False, server_default='0'))
    
    if not column_exists('accounts', 'last_bonus_at'):
        op.add_column('accounts', sa.Column('last_bonus_at', sa.Text(), nullable=True))
    
    # Customer tier tracking
    if not column_exists('accounts', 'customer_tier'):
        op.add_column('accounts', sa.Column('customer_tier', sa.String(50), nullable=False, server_default='registered'))
    
    if not column_exists('accounts', 'dispute_status'):
        op.add_column('accounts', sa.Column('dispute_status', sa.String(50), nullable=True))
    
    # Create indexes for common queries
    if not index_exists('accounts', 'idx_accounts_employment_status'):
        op.create_index('idx_accounts_employment_status', 'accounts', ['employment_status'])
    
    if not index_exists('accounts', 'idx_accounts_customer_tier'):
        op.create_index('idx_accounts_customer_tier', 'accounts', ['customer_tier'])
    
    if not index_exists('accounts', 'idx_accounts_is_fired'):
        op.create_index('idx_accounts_is_fired', 'accounts', ['is_fired'])
    
    # Sync existing data - update demotion_count from times_demoted
    op.execute("UPDATE accounts SET demotion_count = times_demoted WHERE times_demoted > 0")
    
    # Set employment_status for fired employees
    op.execute("UPDATE accounts SET employment_status = 'fired' WHERE is_fired = true")
    
    # Set customer_tier for VIP customers
    op.execute("UPDATE accounts SET customer_tier = 'vip' WHERE type = 'vip'")
    
    # Set customer_tier for blacklisted customers
    op.execute("UPDATE accounts SET customer_tier = 'deregistered' WHERE is_blacklisted = true")


def downgrade():
    # Drop indexes
    op.drop_index('idx_accounts_is_fired', table_name='accounts')
    op.drop_index('idx_accounts_customer_tier', table_name='accounts')
    op.drop_index('idx_accounts_employment_status', table_name='accounts')
    
    # Drop columns
    op.drop_column('accounts', 'dispute_status')
    op.drop_column('accounts', 'customer_tier')
    op.drop_column('accounts', 'last_bonus_at')
    op.drop_column('accounts', 'bonus_count')
    op.drop_column('accounts', 'employment_status')
    op.drop_column('accounts', 'demotion_count')
    op.drop_column('accounts', 'compliment_count')
    op.drop_column('accounts', 'complaint_count')
    op.drop_column('accounts', 'total_rating_count')
    op.drop_column('accounts', 'rolling_avg_rating')
