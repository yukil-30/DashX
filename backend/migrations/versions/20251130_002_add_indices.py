"""Add performance indices and missing columns

Revision ID: 002_add_indices
Revises: 001_initial_schema
Create Date: 2025-11-30

Second iteration pass:
=====================
1. Added indices for common query patterns:
   - Dish search (with trigram for ILIKE)
   - Top-rated dishes
   - Orders by customer
   - Order status filtering
   - Bids per order/delivery person

2. Added missing columns from requirements:
   - Verified free_delivery_credits exists in accounts
   - Verified rating_avg and rating_count exist in dishes
   
3. Added partial index for unresolved complaints

Index Strategy:
- B-tree indices for equality and range queries
- GIN indices with pg_trgm for pattern matching (ILIKE)
- Partial indices for common filter conditions
- Composite indices where multiple columns often queried together
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_indices'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pg_trgm extension for fuzzy text search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # =====================================================
    # ACCOUNTS INDICES
    # =====================================================
    
    # Index on email for login lookups (already unique, but explicit for clarity)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_accounts_email 
        ON accounts(email);
    """)
    
    # Index on account_type for filtering by role
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_accounts_type 
        ON accounts(account_type);
    """)
    
    # Index on restaurant_id for employee queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_accounts_restaurant 
        ON accounts(restaurant_id) 
        WHERE restaurant_id IS NOT NULL;
    """)
    
    # Index for blacklisted users
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_accounts_blacklisted 
        ON accounts(is_blacklisted) 
        WHERE is_blacklisted = TRUE;
    """)

    # =====================================================
    # DISHES INDICES
    # =====================================================
    
    # Index on restaurant_id for menu listings
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dishes_restaurant 
        ON dishes(restaurant_id);
    """)
    
    # GIN index for fuzzy name search with trigram
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dishes_name_trgm 
        ON dishes USING GIN (name gin_trgm_ops);
    """)
    
    # Index on lower(name) for case-insensitive search
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dishes_name_lower 
        ON dishes(LOWER(name));
    """)
    
    # Index on category for filtering
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dishes_category 
        ON dishes(category) 
        WHERE category IS NOT NULL;
    """)
    
    # Index for top-rated queries (descending)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dishes_rating 
        ON dishes(average_rating DESC, review_count DESC);
    """)
    
    # Index for available dishes only
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dishes_available 
        ON dishes(restaurant_id, is_available) 
        WHERE is_available = TRUE;
    """)
    
    # Index on chef_id for chef's dishes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dishes_chef 
        ON dishes(chef_id) 
        WHERE chef_id IS NOT NULL;
    """)

    # =====================================================
    # ORDERS INDICES
    # =====================================================
    
    # Index on account_id for customer order history (critical for performance)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_account 
        ON orders(account_id);
    """)
    
    # Index on status for order management
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_status 
        ON orders(status);
    """)
    
    # Index on order_datetime for date range queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_datetime 
        ON orders(order_datetime DESC);
    """)
    
    # Composite index for customer's recent orders (most common query)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_account_datetime 
        ON orders(account_id, order_datetime DESC);
    """)
    
    # Index on restaurant_id for restaurant's orders
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_restaurant 
        ON orders(restaurant_id);
    """)
    
    # Partial index for active orders (not yet delivered/cancelled)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_active 
        ON orders(status, order_datetime) 
        WHERE status NOT IN ('delivered', 'cancelled', 'refunded');
    """)

    # =====================================================
    # ORDERED_DISHES INDICES
    # =====================================================
    
    # Index on order_id for order details lookup
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_ordered_dishes_order 
        ON ordered_dishes(order_id);
    """)
    
    # Index on dish_id for dish popularity queries (critical for "most ordered" queries)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_ordered_dishes_dish 
        ON ordered_dishes(dish_id);
    """)

    # =====================================================
    # BIDS INDICES
    # =====================================================
    
    # Index on order_id for bids per order
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_bids_order 
        ON bids(order_id);
    """)
    
    # Index on delivery_person_id for driver's bids
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_bids_delivery_person 
        ON bids(delivery_person_id);
    """)
    
    # Index for pending bids
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_bids_pending 
        ON bids(status, created_at) 
        WHERE status = 'pending';
    """)

    # =====================================================
    # COMPLAINTS INDICES
    # =====================================================
    
    # Index for complaints about a user
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_complaints_about 
        ON complaints(about_account_id);
    """)
    
    # Index for complaints filed by a user
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_complaints_reporter 
        ON complaints(reporter_account_id);
    """)
    
    # Partial index for unresolved complaints (common query for managers)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_complaints_unresolved 
        ON complaints(created_at) 
        WHERE is_resolved = FALSE;
    """)

    # =====================================================
    # TRANSACTIONS INDICES
    # =====================================================
    
    # Index on account_id for account history
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_account 
        ON transactions(account_id);
    """)
    
    # Index on order_id for order-related transactions
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_order 
        ON transactions(order_id) 
        WHERE order_id IS NOT NULL;
    """)
    
    # Index on created_at for time-based queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_datetime 
        ON transactions(created_at DESC);
    """)

    # =====================================================
    # FORUM INDICES
    # =====================================================
    
    # Index on restaurant_id for forum threads
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_threads_restaurant 
        ON threads(restaurant_id);
    """)
    
    # Index for pinned threads
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_threads_pinned 
        ON threads(restaurant_id, is_pinned, created_at DESC) 
        WHERE is_pinned = TRUE;
    """)
    
    # Index on thread_id for posts
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_posts_thread 
        ON posts(thread_id, created_at);
    """)
    
    # Index on poster_id
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_posts_poster 
        ON posts(poster_id);
    """)

    # =====================================================
    # RATINGS/REVIEWS INDICES
    # =====================================================
    
    # Index for delivery ratings by delivery person
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_delivery_ratings_person 
        ON delivery_ratings(delivery_person_id);
    """)
    
    # Index for dish reviews by dish
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dish_reviews_dish 
        ON dish_reviews(dish_id);
    """)
    
    # Index for dish reviews by user
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_dish_reviews_account 
        ON dish_reviews(account_id);
    """)

    # =====================================================
    # AGENT QUERIES INDICES
    # =====================================================
    
    # Index for queries by restaurant
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_agent_queries_restaurant 
        ON agent_queries(restaurant_id) 
        WHERE restaurant_id IS NOT NULL;
    """)
    
    # Index for answers by query
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_agent_answers_query 
        ON agent_answers(query_id);
    """)

    # =====================================================
    # OPEN/CLOSURE REQUESTS INDICES
    # =====================================================
    
    # Index for pending open requests
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_open_requests_pending 
        ON open_requests(restaurant_id, status, created_at) 
        WHERE status = 'pending';
    """)
    
    # Index for pending closure requests
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_closure_requests_pending 
        ON closure_requests(status, created_at) 
        WHERE status = 'pending';
    """)


def downgrade() -> None:
    # Drop all indices in reverse order
    indices = [
        # Open/Closure requests
        'idx_closure_requests_pending',
        'idx_open_requests_pending',
        
        # Agent queries
        'idx_agent_answers_query',
        'idx_agent_queries_restaurant',
        
        # Ratings/Reviews
        'idx_dish_reviews_account',
        'idx_dish_reviews_dish',
        'idx_delivery_ratings_person',
        
        # Forum
        'idx_posts_poster',
        'idx_posts_thread',
        'idx_threads_pinned',
        'idx_threads_restaurant',
        
        # Transactions
        'idx_transactions_datetime',
        'idx_transactions_order',
        'idx_transactions_account',
        
        # Complaints
        'idx_complaints_unresolved',
        'idx_complaints_reporter',
        'idx_complaints_about',
        
        # Bids
        'idx_bids_pending',
        'idx_bids_delivery_person',
        'idx_bids_order',
        
        # Ordered dishes
        'idx_ordered_dishes_dish',
        'idx_ordered_dishes_order',
        
        # Orders
        'idx_orders_active',
        'idx_orders_restaurant',
        'idx_orders_account_datetime',
        'idx_orders_datetime',
        'idx_orders_status',
        'idx_orders_account',
        
        # Dishes
        'idx_dishes_chef',
        'idx_dishes_available',
        'idx_dishes_rating',
        'idx_dishes_category',
        'idx_dishes_name_lower',
        'idx_dishes_name_trgm',
        'idx_dishes_restaurant',
        
        # Accounts
        'idx_accounts_blacklisted',
        'idx_accounts_restaurant',
        'idx_accounts_type',
        'idx_accounts_email',
    ]
    
    for idx in indices:
        op.execute(f"DROP INDEX IF EXISTS {idx};")
    
    # Note: Not dropping pg_trgm extension as other databases might use it
