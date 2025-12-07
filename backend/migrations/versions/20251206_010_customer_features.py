"""Customer features - Reviews, VIP tracking, Profiles

Revision ID: 20251206_010
Revises: 20251202_009
Create Date: 2025-12-06

Adds:
- dish_reviews table for per-dish customer reviews
- order_delivery_reviews table for delivery reviews per order
- vip_history table for tracking VIP status changes
- account_profiles table for extended profile info
- total_spent_cents column to accounts for VIP eligibility tracking
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '20251206_010'
down_revision = '20251202_009_voice_reports'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to accounts table
    op.add_column('accounts', sa.Column('total_spent_cents', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('accounts', sa.Column('unresolved_complaints_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('accounts', sa.Column('is_vip', sa.Boolean(), nullable=False, server_default='0'))
    
    # Create dish_reviews table
    op.create_table(
        'dish_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dish_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('review_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['dish_id'], ['dishes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.ID'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_dish_review_rating')
    )
    op.create_index('idx_dish_reviews_dish', 'dish_reviews', ['dish_id'])
    op.create_index('idx_dish_reviews_account', 'dish_reviews', ['account_id'])
    op.create_index('idx_dish_reviews_order', 'dish_reviews', ['order_id'])
    
    # Create order_delivery_reviews table
    op.create_table(
        'order_delivery_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('delivery_person_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('review_text', sa.Text(), nullable=True),
        sa.Column('on_time', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['delivery_person_id'], ['accounts.ID'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['accounts.ID'], ondelete='CASCADE'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_delivery_review_rating'),
        sa.UniqueConstraint('order_id', name='uq_order_delivery_review')
    )
    op.create_index('idx_delivery_reviews_order', 'order_delivery_reviews', ['order_id'])
    op.create_index('idx_delivery_reviews_delivery_person', 'order_delivery_reviews', ['delivery_person_id'])
    
    # Create vip_history table
    op.create_table(
        'vip_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('previous_type', sa.String(50), nullable=False),
        sa.Column('new_type', sa.String(50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.ID'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['accounts.ID'], ondelete='SET NULL')
    )
    op.create_index('idx_vip_history_account', 'vip_history', ['account_id'])
    
    # Create account_profiles table
    op.create_table(
        'account_profiles',
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('profile_picture', sa.Text(), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('specialty', sa.String(255), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('account_id'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.ID'], ondelete='CASCADE')
    )
    
    # Create forum_threads table
    op.create_table(
        'forum_threads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('topic_type', sa.String(50), nullable=False),
        sa.Column('topic_id', sa.Integer(), nullable=True),
        sa.Column('author_id', sa.Integer(), nullable=True),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['author_id'], ['accounts.ID'], ondelete='SET NULL')
    )
    op.create_index('idx_forum_threads_topic', 'forum_threads', ['topic_type', 'topic_id'])
    op.create_index('idx_forum_threads_author', 'forum_threads', ['author_id'])
    
    # Create forum_posts table
    op.create_table(
        'forum_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['thread_id'], ['forum_threads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['accounts.ID'], ondelete='SET NULL')
    )
    op.create_index('idx_forum_posts_thread', 'forum_posts', ['thread_id'])
    op.create_index('idx_forum_posts_author', 'forum_posts', ['author_id'])


def downgrade():
    op.drop_index('idx_forum_posts_author', 'forum_posts')
    op.drop_index('idx_forum_posts_thread', 'forum_posts')
    op.drop_table('forum_posts')
    op.drop_index('idx_forum_threads_author', 'forum_threads')
    op.drop_index('idx_forum_threads_topic', 'forum_threads')
    op.drop_table('forum_threads')
    op.drop_table('account_profiles')
    op.drop_index('idx_vip_history_account', 'vip_history')
    op.drop_table('vip_history')
    op.drop_index('idx_delivery_reviews_delivery_person', 'order_delivery_reviews')
    op.drop_index('idx_delivery_reviews_order', 'order_delivery_reviews')
    op.drop_table('order_delivery_reviews')
    op.drop_index('idx_dish_reviews_order', 'dish_reviews')
    op.drop_index('idx_dish_reviews_account', 'dish_reviews')
    op.drop_index('idx_dish_reviews_dish', 'dish_reviews')
    op.drop_table('dish_reviews')
    op.drop_column('accounts', 'is_vip')
    op.drop_column('accounts', 'unresolved_complaints_count')
    op.drop_column('accounts', 'total_spent_cents')
