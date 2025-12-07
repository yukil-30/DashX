"""voice reports system

Revision ID: 20251202_009
Revises: 20251201_008
Create Date: 2025-12-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '20251202_009_voice_reports'
down_revision = '008_chat_system'
branch_labels = None
depends_on = None


def upgrade():
    """Create voice_reports table for voice-based complaint/compliment system"""
    
    # Ensure table doesn't exist from failed previous runs
    op.execute("DROP TABLE IF EXISTS voice_reports CASCADE")

    op.create_table(
        'voice_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submitter_id', sa.Integer(), nullable=False),
        sa.Column('audio_file_path', sa.Text(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=False, server_default='audio/mpeg'),
        sa.Column('transcription', sa.Text(), nullable=True),
        sa.Column('sentiment', sa.String(50), nullable=True),  # complaint, compliment, neutral
        sa.Column('subjects', JSONB, nullable=True),  # Extracted subjects (chef, driver, staff, etc.)
        sa.Column('auto_labels', JSONB, nullable=True),  # Auto-generated labels like "Complaint Chef"
        sa.Column('confidence_score', sa.Numeric(3, 2), nullable=True),  # NLP confidence 0.00-1.00
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),  # pending, transcribed, analyzed, resolved
        sa.Column('is_processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('related_order_id', sa.Integer(), nullable=True),
        sa.Column('related_account_id', sa.Integer(), nullable=True),  # Person being reported about
        sa.Column('processing_error', sa.Text(), nullable=True),  # Error message if processing fails
        sa.Column('manager_notes', sa.Text(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.Text(), nullable=True),  # ISO timestamp
        sa.Column('created_at', sa.Text(), nullable=False),  # ISO timestamp
        sa.Column('updated_at', sa.Text(), nullable=False),  # ISO timestamp
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['submitter_id'], ['accounts.ID'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['related_account_id'], ['accounts.ID'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by'], ['accounts.ID'], ondelete='SET NULL')
    )
    
    # Create indices for efficient queries
    op.create_index('idx_voice_reports_submitter', 'voice_reports', ['submitter_id'])
    op.create_index('idx_voice_reports_status', 'voice_reports', ['status'])
    op.create_index('idx_voice_reports_sentiment', 'voice_reports', ['sentiment'])
    op.create_index('idx_voice_reports_unprocessed', 'voice_reports', ['is_processed'], 
                    postgresql_where=sa.text('is_processed = false'))
    op.create_index('idx_voice_reports_created', 'voice_reports', ['created_at'])
    op.create_index('idx_voice_reports_related_account', 'voice_reports', ['related_account_id'])


def downgrade():
    """Drop voice_reports table and indices"""
    op.drop_index('idx_voice_reports_related_account', table_name='voice_reports')
    op.drop_index('idx_voice_reports_created', table_name='voice_reports')
    op.drop_index('idx_voice_reports_unprocessed', table_name='voice_reports')
    op.drop_index('idx_voice_reports_sentiment', table_name='voice_reports')
    op.drop_index('idx_voice_reports_status', table_name='voice_reports')
    op.drop_index('idx_voice_reports_submitter', table_name='voice_reports')
    op.drop_table('voice_reports')
