"""Add knowledge base and chat log tables for chat flow

Revision ID: 008_chat_system
Revises: 20251202_004_authoritative_schema
Create Date: 2025-12-01

Design Decisions:
=================
1. KNOWLEDGE_BASE: Uses PostgreSQL full-text search (tsvector) for efficient keyword matching.
   - question/answer pairs with keywords and confidence score
   - author tracking for accountability
   - is_active flag for soft-delete/disable
   
2. CHAT_LOG: Stores all chat interactions for audit and rating.
   - source field indicates 'kb' (knowledge base) or 'llm' (LLM-generated)
   - rating 0-5 where 0 = flagged for review
   - kb_entry_id links to knowledge_base if source='kb'
   
3. FULL-TEXT SEARCH: Using GIN index on tsvector for fast keyword matching.
   PostgreSQL's to_tsvector and to_tsquery provide robust text search.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '008_chat_system'
down_revision: Union[str, None] = '20251202_004_authoritative_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =====================================================
    # TABLE: knowledge_base
    # Stores FAQ/knowledge entries for KB search
    # =====================================================
    op.execute("""
        CREATE TABLE knowledge_base (
            id SERIAL PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            keywords TEXT,  -- Comma-separated keywords for additional matching
            confidence NUMERIC(3, 2) NOT NULL DEFAULT 0.80,  -- Default confidence score
            author_id INTEGER REFERENCES accounts("ID") ON DELETE SET NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Add full-text search vector column
    op.execute("""
        ALTER TABLE knowledge_base 
        ADD COLUMN search_vector tsvector 
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(question, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(keywords, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(answer, '')), 'C')
        ) STORED;
    """)
    
    # Create GIN index for fast full-text search
    op.execute("""
        CREATE INDEX idx_knowledge_base_search 
        ON knowledge_base USING GIN(search_vector);
    """)
    
    # Create index for active entries
    op.execute("""
        CREATE INDEX idx_knowledge_base_active 
        ON knowledge_base(is_active) WHERE is_active = TRUE;
    """)

    # =====================================================
    # TABLE: chat_log
    # Stores all chat interactions for audit and rating
    # =====================================================
    op.execute("""
        CREATE TABLE chat_log (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES accounts("ID") ON DELETE CASCADE,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            source VARCHAR(10) NOT NULL CHECK (source IN ('kb', 'llm')),
            kb_entry_id INTEGER REFERENCES knowledge_base(id) ON DELETE SET NULL,
            confidence NUMERIC(3, 2),  -- Confidence of the match/response
            rating INTEGER CHECK (rating >= 0 AND rating <= 5),  -- 0 = flagged, 1-5 = satisfaction
            flagged BOOLEAN NOT NULL DEFAULT FALSE,
            reviewed BOOLEAN NOT NULL DEFAULT FALSE,  -- Manager has reviewed flagged entry
            reviewed_by INTEGER REFERENCES accounts("ID") ON DELETE SET NULL,
            reviewed_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Create indices for common queries
    op.execute("""
        CREATE INDEX idx_chat_log_user 
        ON chat_log(user_id);
    """)
    
    op.execute("""
        CREATE INDEX idx_chat_log_flagged 
        ON chat_log(flagged) WHERE flagged = TRUE;
    """)
    
    op.execute("""
        CREATE INDEX idx_chat_log_source 
        ON chat_log(source);
    """)

    # Apply updated_at trigger to knowledge_base
    op.execute("""
        CREATE TRIGGER update_knowledge_base_updated_at
        BEFORE UPDATE ON knowledge_base
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_knowledge_base_updated_at ON knowledge_base;")
    op.execute("DROP INDEX IF EXISTS idx_chat_log_source;")
    op.execute("DROP INDEX IF EXISTS idx_chat_log_flagged;")
    op.execute("DROP INDEX IF EXISTS idx_chat_log_user;")
    op.execute("DROP TABLE IF EXISTS chat_log CASCADE;")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_base_active;")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_base_search;")
    op.execute("DROP TABLE IF EXISTS knowledge_base CASCADE;")
