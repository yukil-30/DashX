"""Create initial DashX schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-11-30

Design Decisions & Ambiguity Resolutions:
==========================================
1. ACCOUNT TYPE: Using PostgreSQL ENUM for account types to ensure data integrity.
   Values: visitor, customer, vip, chef, delivery, manager
   
2. BALANCE & COSTS: Using INTEGER for monetary values (cents) to avoid floating-point 
   precision issues. All prices, costs, balances are stored in cents (e.g., $10.99 = 1099).

3. COMPLAINT TABLE: The diagram shows 'accountID' and 'filer' which is ambiguous.
   Resolution: Using 'about_account_id' (person being complained/complimented about)
   and 'reporter_account_id' (person filing the complaint/compliment).

4. WARNINGS LIFECYCLE: Added 'warnings' counter (default 0) and 'is_blacklisted' boolean.
   Business rule: Users with warnings >= 3 can be blacklisted.

5. FREE_DELIVERY_CREDITS: Added to accounts for promotional purposes.

6. TRANSACTIONS TABLE: Added for audit trail of all financial transactions 
   (deposits, withdrawals, order payments). This is recommended for any financial system.

7. DELIVERY_RATINGS: Using a separate table with account_id FK rather than duplicating
   rating info in accounts table - allows for future expansion.

8. PICTURE FIELD: Using TEXT for image paths/URLs. Could store JSON for multiple images.

9. TIMESTAMPS: All tables include created_at, some have updated_at for tracking.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types first
    op.execute("""
        CREATE TYPE account_type AS ENUM (
            'visitor', 'customer', 'vip', 'chef', 'delivery', 'manager'
        );
    """)
    
    op.execute("""
        CREATE TYPE order_status AS ENUM (
            'pending', 'confirmed', 'preparing', 'ready', 'out_for_delivery', 
            'delivered', 'cancelled', 'refunded'
        );
    """)
    
    op.execute("""
        CREATE TYPE feedback_type AS ENUM ('complaint', 'compliment');
    """)
    
    op.execute("""
        CREATE TYPE transaction_type AS ENUM (
            'deposit', 'withdrawal', 'order_payment', 'order_refund', 
            'wage_payment', 'tip', 'delivery_fee'
        );
    """)
    
    op.execute("""
        CREATE TYPE bid_status AS ENUM ('pending', 'accepted', 'rejected', 'expired');
    """)

    # =====================================================
    # TABLE: restaurant
    # The restaurant entity - central to the system
    # =====================================================
    op.execute("""
        CREATE TABLE restaurant (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            address TEXT NOT NULL,
            phone VARCHAR(20),
            email VARCHAR(255),
            description TEXT,
            opening_hours JSONB,  -- Flexible hours storage: {"monday": {"open": "09:00", "close": "21:00"}, ...}
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # =====================================================
    # TABLE: accounts
    # All users: visitors, customers, VIPs, employees
    # =====================================================
    op.execute("""
        CREATE TABLE accounts (
            id SERIAL PRIMARY KEY,
            restaurant_id INTEGER REFERENCES restaurant(id) ON DELETE SET NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,  -- Store bcrypt/argon2 hash, never plain text
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            phone VARCHAR(20),
            address TEXT,  -- Delivery address for customers
            account_type account_type NOT NULL DEFAULT 'visitor',
            balance INTEGER NOT NULL DEFAULT 0,  -- In cents, can be negative for debt
            wage INTEGER,  -- Hourly wage in cents for employees (chef, delivery, manager)
            warnings INTEGER NOT NULL DEFAULT 0,  -- Count of warnings received
            is_blacklisted BOOLEAN NOT NULL DEFAULT FALSE,
            free_delivery_credits INTEGER NOT NULL DEFAULT 0,  -- Number of free deliveries
            last_login_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # =====================================================
    # TABLE: dishes
    # Menu items available at the restaurant
    # =====================================================
    op.execute("""
        CREATE TABLE dishes (
            id SERIAL PRIMARY KEY,
            restaurant_id INTEGER NOT NULL REFERENCES restaurant(id) ON DELETE CASCADE,
            chef_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,  -- Chef who created the dish
            name VARCHAR(255) NOT NULL,
            description TEXT,
            price INTEGER NOT NULL CHECK (price >= 0),  -- In cents
            picture TEXT,  -- URL or path to image
            category VARCHAR(100),  -- appetizer, main, dessert, beverage, etc.
            is_available BOOLEAN NOT NULL DEFAULT TRUE,
            is_special BOOLEAN NOT NULL DEFAULT FALSE,  -- Featured/daily special
            average_rating NUMERIC(3,2) DEFAULT 0.00 CHECK (average_rating >= 0 AND average_rating <= 5),
            review_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # =====================================================
    # TABLE: orders
    # Customer orders
    # =====================================================
    op.execute("""
        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
            restaurant_id INTEGER NOT NULL REFERENCES restaurant(id) ON DELETE RESTRICT,
            order_datetime TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            final_cost INTEGER NOT NULL CHECK (final_cost >= 0),  -- Total in cents
            subtotal INTEGER NOT NULL CHECK (subtotal >= 0),  -- Before fees/discounts
            delivery_fee INTEGER NOT NULL DEFAULT 0,  -- Delivery fee in cents
            tip INTEGER NOT NULL DEFAULT 0,  -- Tip in cents
            discount INTEGER NOT NULL DEFAULT 0,  -- Discount applied in cents
            status order_status NOT NULL DEFAULT 'pending',
            delivery_address TEXT,
            note TEXT,  -- Special instructions
            is_delivery BOOLEAN NOT NULL DEFAULT TRUE,  -- False for pickup
            estimated_ready_time TIMESTAMP WITH TIME ZONE,
            actual_ready_time TIMESTAMP WITH TIME ZONE,
            delivered_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # =====================================================
    # TABLE: ordered_dishes (junction table)
    # Links orders to dishes with quantities
    # =====================================================
    op.execute("""
        CREATE TABLE ordered_dishes (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            dish_id INTEGER NOT NULL REFERENCES dishes(id) ON DELETE RESTRICT,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price INTEGER NOT NULL,  -- Price at time of order (in cents)
            special_instructions TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # =====================================================
    # TABLE: bids
    # Delivery person bids on orders
    # =====================================================
    op.execute("""
        CREATE TABLE bids (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            delivery_person_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            bid_amount INTEGER NOT NULL CHECK (bid_amount >= 0),  -- In cents
            status bid_status NOT NULL DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(order_id, delivery_person_id)  -- One bid per delivery person per order
        );
    """)
    
    # -- Add accepted_bid_id to orders (circular FK, add after bids table exists)
    op.execute("""
        ALTER TABLE orders 
        ADD COLUMN accepted_bid_id INTEGER REFERENCES bids(id) ON DELETE SET NULL;
    """)

    # =====================================================
    # TABLE: complaints
    # Unified table for complaints and compliments
    # =====================================================
    op.execute("""
        CREATE TABLE complaints (
            id SERIAL PRIMARY KEY,
            about_account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            reporter_account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,  -- Optional: related order
            feedback_type feedback_type NOT NULL,
            description TEXT NOT NULL,
            is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
            manager_decision TEXT,
            resolved_by_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            resolved_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (about_account_id != reporter_account_id)  -- Can't file about yourself
        );
    """)

    # =====================================================
    # TABLE: threads
    # Forum discussion threads
    # =====================================================
    op.execute("""
        CREATE TABLE threads (
            id SERIAL PRIMARY KEY,
            restaurant_id INTEGER NOT NULL REFERENCES restaurant(id) ON DELETE CASCADE,
            topic VARCHAR(255) NOT NULL,
            created_by_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
            is_locked BOOLEAN NOT NULL DEFAULT FALSE,
            view_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # =====================================================
    # TABLE: posts
    # Forum posts within threads
    # =====================================================
    op.execute("""
        CREATE TABLE posts (
            id SERIAL PRIMARY KEY,
            thread_id INTEGER NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
            poster_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            parent_post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,  -- For nested replies
            title VARCHAR(255),
            body TEXT NOT NULL,
            is_edited BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # =====================================================
    # TABLE: agent_queries
    # AI/LLM queries from users
    # =====================================================
    op.execute("""
        CREATE TABLE agent_queries (
            id SERIAL PRIMARY KEY,
            account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            restaurant_id INTEGER REFERENCES restaurant(id) ON DELETE CASCADE,
            question TEXT NOT NULL,
            context JSONB,  -- Additional context for the query
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # =====================================================
    # TABLE: agent_answers
    # AI/LLM responses to queries
    # =====================================================
    op.execute("""
        CREATE TABLE agent_answers (
            id SERIAL PRIMARY KEY,
            query_id INTEGER NOT NULL REFERENCES agent_queries(id) ON DELETE CASCADE,
            author_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,  -- NULL for AI answers
            answer TEXT NOT NULL,
            is_ai_generated BOOLEAN NOT NULL DEFAULT TRUE,
            average_rating NUMERIC(3,2) DEFAULT 0.00 CHECK (average_rating >= 0 AND average_rating <= 5),
            review_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # =====================================================
    # TABLE: delivery_ratings
    # Ratings for delivery personnel
    # =====================================================
    op.execute("""
        CREATE TABLE delivery_ratings (
            id SERIAL PRIMARY KEY,
            delivery_person_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            rater_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(order_id, rater_id)  -- One rating per order per rater
        );
    """)

    # =====================================================
    # TABLE: dish_reviews
    # Customer reviews for dishes
    # =====================================================
    op.execute("""
        CREATE TABLE dish_reviews (
            id SERIAL PRIMARY KEY,
            dish_id INTEGER NOT NULL REFERENCES dishes(id) ON DELETE CASCADE,
            account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            review_text TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dish_id, account_id, order_id)  -- One review per dish per order
        );
    """)

    # =====================================================
    # TABLE: open_requests
    # Applications to join a restaurant (employee applications)
    # =====================================================
    op.execute("""
        CREATE TABLE open_requests (
            id SERIAL PRIMARY KEY,
            restaurant_id INTEGER NOT NULL REFERENCES restaurant(id) ON DELETE CASCADE,
            email VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,  -- Temporary password for the application
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            phone VARCHAR(20),
            requested_role account_type NOT NULL,
            resume_url TEXT,
            cover_letter TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
            reviewed_by_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            reviewed_at TIMESTAMP WITH TIME ZONE,
            rejection_reason TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # =====================================================
    # TABLE: closure_requests
    # Account closure/deletion requests
    # =====================================================
    op.execute("""
        CREATE TABLE closure_requests (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            reason TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
            reviewed_by_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            reviewed_at TIMESTAMP WITH TIME ZONE,
            rejection_reason TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # =====================================================
    # TABLE: transactions
    # Financial audit trail (RECOMMENDED for any financial system)
    # =====================================================
    op.execute("""
        CREATE TABLE transactions (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
            order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,
            transaction_type transaction_type NOT NULL,
            amount INTEGER NOT NULL,  -- In cents, positive for credit, negative for debit
            balance_before INTEGER NOT NULL,  -- Account balance before transaction
            balance_after INTEGER NOT NULL,  -- Account balance after transaction
            description TEXT,
            reference_id VARCHAR(100),  -- External reference (payment gateway ID, etc.)
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # =====================================================
    # TABLE: vip_history
    # Track VIP status changes
    # =====================================================
    op.execute("""
        CREATE TABLE vip_history (
            id SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            previous_type account_type NOT NULL,
            new_type account_type NOT NULL,
            reason TEXT,
            changed_by_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # =====================================================
    # Create trigger function for updated_at
    # =====================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Apply updated_at trigger to relevant tables
    for table in ['restaurant', 'accounts', 'dishes', 'orders', 'bids', 
                  'complaints', 'threads', 'posts', 'open_requests', 
                  'closure_requests', 'dish_reviews']:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    # Drop triggers first
    for table in ['restaurant', 'accounts', 'dishes', 'orders', 'bids', 
                  'complaints', 'threads', 'posts', 'open_requests', 
                  'closure_requests', 'dish_reviews']:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};")
    
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Drop tables in reverse dependency order
    tables = [
        'vip_history',
        'transactions',
        'closure_requests',
        'open_requests',
        'dish_reviews',
        'delivery_ratings',
        'agent_answers',
        'agent_queries',
        'posts',
        'threads',
        'complaints',
        'ordered_dishes',
    ]
    
    for table in tables:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
    
    # Remove accepted_bid_id from orders before dropping bids
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS accepted_bid_id;")
    
    op.execute("DROP TABLE IF EXISTS bids CASCADE;")
    op.execute("DROP TABLE IF EXISTS orders CASCADE;")
    op.execute("DROP TABLE IF EXISTS dishes CASCADE;")
    op.execute("DROP TABLE IF EXISTS accounts CASCADE;")
    op.execute("DROP TABLE IF EXISTS restaurant CASCADE;")

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS bid_status;")
    op.execute("DROP TYPE IF EXISTS transaction_type;")
    op.execute("DROP TYPE IF EXISTS feedback_type;")
    op.execute("DROP TYPE IF EXISTS order_status;")
    op.execute("DROP TYPE IF EXISTS account_type;")
