"""Add KB contributions table for customer submissions

Revision ID: 20251210_017
Revises: 20251211_016
Create Date: 2025-12-10

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251210_017'
down_revision = '20251211_016'
branch_labels = None
depends_on = None


def upgrade():
    # Create kb_contributions table for customer-submitted KB entries
    op.create_table(
        'kb_contributions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('submitter_id', sa.Integer(), sa.ForeignKey('accounts.ID', ondelete='CASCADE'), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), sa.ForeignKey('accounts.ID', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.Text(), nullable=True),
        sa.Column('created_kb_entry_id', sa.Integer(), sa.ForeignKey('knowledge_base.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=True),
    )
    
    # Add index for efficient querying by status
    op.create_index('idx_kb_contributions_status', 'kb_contributions', ['status'])
    op.create_index('idx_kb_contributions_submitter', 'kb_contributions', ['submitter_id'])


def downgrade():
    op.drop_index('idx_kb_contributions_submitter', table_name='kb_contributions')
    op.drop_index('idx_kb_contributions_status', table_name='kb_contributions')
    op.drop_table('kb_contributions')
