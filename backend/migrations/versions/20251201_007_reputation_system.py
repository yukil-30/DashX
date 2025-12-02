"""Add reputation system: complaints, audit log, blacklist, chef tracking

Revision ID: 007_reputation_system
Revises: 006_bidding_enhancements
Create Date: 2025-12-01

This migration adds:
1. Enhanced complaint table with status, order_id, resolution tracking
2. Audit log table for immutable tracking of all reputation-related actions
3. Blacklist table for permanently banned users
4. Chef tracking: times_demoted, is_fired columns on accounts
5. Chef ratings tracking on dishes
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007_reputation_system'
down_revision: Union[str, None] = '006_bidding_enhancements'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add chef tracking columns to accounts table
    op.execute("""
        ALTER TABLE accounts 
        ADD COLUMN IF NOT EXISTS times_demoted INTEGER NOT NULL DEFAULT 0;
    """)
    op.execute("""
        ALTER TABLE accounts 
        ADD COLUMN IF NOT EXISTS is_fired BOOLEAN NOT NULL DEFAULT FALSE;
    """)
    op.execute("""
        ALTER TABLE accounts 
        ADD COLUMN IF NOT EXISTS is_blacklisted BOOLEAN NOT NULL DEFAULT FALSE;
    """)
    op.execute("""
        ALTER TABLE accounts 
        ADD COLUMN IF NOT EXISTS previous_type VARCHAR(50);
    """)

    # Add columns to complaint table for enhanced tracking
    op.execute("""
        ALTER TABLE complaint 
        ADD COLUMN IF NOT EXISTS order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL;
    """)
    op.execute("""
        ALTER TABLE complaint 
        ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'pending';
    """)
    op.execute("""
        ALTER TABLE complaint 
        ADD COLUMN IF NOT EXISTS resolution VARCHAR(50);
    """)
    op.execute("""
        ALTER TABLE complaint 
        ADD COLUMN IF NOT EXISTS resolved_by INTEGER REFERENCES accounts("ID") ON DELETE SET NULL;
    """)
    op.execute("""
        ALTER TABLE complaint 
        ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP WITH TIME ZONE;
    """)
    op.execute("""
        ALTER TABLE complaint 
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;
    """)

    # Create audit_log table for immutable tracking
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            action_type VARCHAR(100) NOT NULL,
            actor_id INTEGER REFERENCES accounts("ID") ON DELETE SET NULL,
            target_id INTEGER REFERENCES accounts("ID") ON DELETE SET NULL,
            complaint_id INTEGER REFERENCES complaint(id) ON DELETE SET NULL,
            order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,
            details JSONB,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create blacklist table
    op.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            reason TEXT,
            original_account_id INTEGER,
            blacklisted_by INTEGER REFERENCES accounts("ID") ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create manager_notifications table for system alerts
    op.execute("""
        CREATE TABLE IF NOT EXISTS manager_notifications (
            id SERIAL PRIMARY KEY,
            notification_type VARCHAR(100) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            related_account_id INTEGER REFERENCES accounts("ID") ON DELETE SET NULL,
            related_order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,
            is_read BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create indices for performance
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_complaint_status ON complaint(status);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_complaint_about ON complaint("accountID");
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_complaint_filer ON complaint(filer);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_log_target ON audit_log(target_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_notifications_unread ON manager_notifications(is_read) WHERE is_read = FALSE;
    """)


def downgrade() -> None:
    # Drop indices
    op.execute("DROP INDEX IF EXISTS idx_notifications_unread;")
    op.execute("DROP INDEX IF EXISTS idx_audit_log_created;")
    op.execute("DROP INDEX IF EXISTS idx_audit_log_actor;")
    op.execute("DROP INDEX IF EXISTS idx_audit_log_target;")
    op.execute("DROP INDEX IF EXISTS idx_complaint_filer;")
    op.execute("DROP INDEX IF EXISTS idx_complaint_about;")
    op.execute("DROP INDEX IF EXISTS idx_complaint_status;")

    # Drop new tables
    op.execute("DROP TABLE IF EXISTS manager_notifications;")
    op.execute("DROP TABLE IF EXISTS blacklist;")
    op.execute("DROP TABLE IF EXISTS audit_log;")

    # Remove columns from complaint table
    op.execute("ALTER TABLE complaint DROP COLUMN IF EXISTS created_at;")
    op.execute("ALTER TABLE complaint DROP COLUMN IF EXISTS resolved_at;")
    op.execute("ALTER TABLE complaint DROP COLUMN IF EXISTS resolved_by;")
    op.execute("ALTER TABLE complaint DROP COLUMN IF EXISTS resolution;")
    op.execute("ALTER TABLE complaint DROP COLUMN IF EXISTS status;")
    op.execute("ALTER TABLE complaint DROP COLUMN IF EXISTS order_id;")

    # Remove columns from accounts table
    op.execute("ALTER TABLE accounts DROP COLUMN IF EXISTS previous_type;")
    op.execute("ALTER TABLE accounts DROP COLUMN IF EXISTS is_blacklisted;")
    op.execute("ALTER TABLE accounts DROP COLUMN IF EXISTS is_fired;")
    op.execute("ALTER TABLE accounts DROP COLUMN IF EXISTS times_demoted;")
