"""Reset to authoritative schema

Revision ID: 004_authoritative_schema
Revises: 003_dish_images
Create Date: 2025-12-02

This migration drops all existing tables and recreates them to exactly match
the authoritative database schema. No deviations allowed.

Authoritative Schema Tables:
===========================
1. restaurant (id, name, address)
2. accounts (ID, restaurantID, email, password, warnings, type, balance, wage)
3. dishes (id, restaurantID, name, description, cost, picture, average_rating, reviews, chefID)
4. orders (id, accountID, dateTime, finalCost, status, bidID, note)
5. ordered_dishes (DishID, orderID, quantity) - composite PK
6. bid (id, deliveryPersonID, orderID, bidAmount)
7. thread (id, topic)
8. post (id, threadID, posterID, title, body)
9. agent_query (id, accountID, question)
10. agent_answer (id, queryID, answer, authorID, average_rating, reviews)
11. DeliveryRating (accountID (PK), averageRating, reviews)
12. complaint (id, accountID, type, description, filer)
13. closureRequest (accountID (PK))
14. openRequest (id, email, password)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_authoritative_schema'
down_revision: Union[str, None] = '003_dish_images'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop all existing triggers first
    for table in ['restaurant', 'accounts', 'dishes', 'orders', 'bids', 
                  'complaints', 'threads', 'posts', 'open_requests', 
                  'closure_requests', 'dish_reviews']:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};")
    
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Drop all existing tables in reverse dependency order
    tables_to_drop = [
        'dish_images',
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
        'bids',
        'orders',
        'dishes',
        'accounts',
        'restaurant',
    ]
    
    for table in tables_to_drop:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
    
    # Drop existing ENUM types
    op.execute("DROP TYPE IF EXISTS bid_status;")
    op.execute("DROP TYPE IF EXISTS transaction_type;")
    op.execute("DROP TYPE IF EXISTS feedback_type;")
    op.execute("DROP TYPE IF EXISTS order_status;")
    op.execute("DROP TYPE IF EXISTS account_type;")

    # =====================================================
    # CREATE AUTHORITATIVE SCHEMA - EXACT MATCH REQUIRED
    # =====================================================

    # TABLE: restaurant
    op.execute("""
        CREATE TABLE restaurant (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            address TEXT NOT NULL
        );
    """)

    # TABLE: accounts
    op.execute("""
        CREATE TABLE accounts (
            "ID" SERIAL PRIMARY KEY,
            "restaurantID" INTEGER REFERENCES restaurant(id) ON DELETE SET NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            warnings INTEGER NOT NULL DEFAULT 0,
            type VARCHAR(50) NOT NULL DEFAULT 'visitor',
            balance INTEGER NOT NULL DEFAULT 0,
            wage INTEGER
        );
    """)

    # TABLE: dishes
    op.execute("""
        CREATE TABLE dishes (
            id SERIAL PRIMARY KEY,
            "restaurantID" INTEGER NOT NULL REFERENCES restaurant(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            cost INTEGER NOT NULL CHECK (cost >= 0),
            picture TEXT,
            average_rating NUMERIC(3,2) DEFAULT 0.00,
            reviews INTEGER NOT NULL DEFAULT 0,
            "chefID" INTEGER REFERENCES accounts("ID") ON DELETE SET NULL
        );
    """)

    # TABLE: orders
    op.execute("""
        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            "accountID" INTEGER NOT NULL REFERENCES accounts("ID") ON DELETE RESTRICT,
            "dateTime" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "finalCost" INTEGER NOT NULL CHECK ("finalCost" >= 0),
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            "bidID" INTEGER,
            note TEXT
        );
    """)

    # TABLE: bid
    op.execute("""
        CREATE TABLE bid (
            id SERIAL PRIMARY KEY,
            "deliveryPersonID" INTEGER NOT NULL REFERENCES accounts("ID") ON DELETE CASCADE,
            "orderID" INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            "bidAmount" INTEGER NOT NULL CHECK ("bidAmount" >= 0)
        );
    """)

    # Add FK constraint for bidID in orders (after bid table exists)
    op.execute("""
        ALTER TABLE orders 
        ADD CONSTRAINT fk_orders_bid 
        FOREIGN KEY ("bidID") REFERENCES bid(id) ON DELETE SET NULL;
    """)

    # TABLE: ordered_dishes (composite primary key)
    op.execute("""
        CREATE TABLE ordered_dishes (
            "DishID" INTEGER NOT NULL REFERENCES dishes(id) ON DELETE RESTRICT,
            "orderID" INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            PRIMARY KEY ("DishID", "orderID")
        );
    """)

    # TABLE: thread
    op.execute("""
        CREATE TABLE thread (
            id SERIAL PRIMARY KEY,
            topic VARCHAR(255) NOT NULL
        );
    """)

    # TABLE: post
    op.execute("""
        CREATE TABLE post (
            id SERIAL PRIMARY KEY,
            "threadID" INTEGER NOT NULL REFERENCES thread(id) ON DELETE CASCADE,
            "posterID" INTEGER NOT NULL REFERENCES accounts("ID") ON DELETE CASCADE,
            title VARCHAR(255),
            body TEXT NOT NULL
        );
    """)

    # TABLE: agent_query
    op.execute("""
        CREATE TABLE agent_query (
            id SERIAL PRIMARY KEY,
            "accountID" INTEGER REFERENCES accounts("ID") ON DELETE SET NULL,
            question TEXT NOT NULL
        );
    """)

    # TABLE: agent_answer
    op.execute("""
        CREATE TABLE agent_answer (
            id SERIAL PRIMARY KEY,
            "queryID" INTEGER NOT NULL REFERENCES agent_query(id) ON DELETE CASCADE,
            answer TEXT NOT NULL,
            "authorID" INTEGER REFERENCES accounts("ID") ON DELETE SET NULL,
            average_rating NUMERIC(3,2) DEFAULT 0.00,
            reviews INTEGER NOT NULL DEFAULT 0
        );
    """)

    # TABLE: DeliveryRating (accountID is PK)
    op.execute("""
        CREATE TABLE "DeliveryRating" (
            "accountID" INTEGER PRIMARY KEY REFERENCES accounts("ID") ON DELETE CASCADE,
            "averageRating" NUMERIC(3,2) DEFAULT 0.00,
            reviews INTEGER NOT NULL DEFAULT 0
        );
    """)

    # TABLE: complaint
    op.execute("""
        CREATE TABLE complaint (
            id SERIAL PRIMARY KEY,
            "accountID" INTEGER NOT NULL REFERENCES accounts("ID") ON DELETE CASCADE,
            type VARCHAR(50) NOT NULL,
            description TEXT NOT NULL,
            filer INTEGER NOT NULL REFERENCES accounts("ID") ON DELETE CASCADE
        );
    """)

    # TABLE: closureRequest (accountID is PK)
    op.execute("""
        CREATE TABLE "closureRequest" (
            "accountID" INTEGER PRIMARY KEY REFERENCES accounts("ID") ON DELETE CASCADE
        );
    """)

    # TABLE: openRequest
    op.execute("""
        CREATE TABLE "openRequest" (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL
        );
    """)


def downgrade() -> None:
    # Drop all authoritative schema tables
    tables_to_drop = [
        '"openRequest"',
        '"closureRequest"',
        'complaint',
        '"DeliveryRating"',
        'agent_answer',
        'agent_query',
        'post',
        'thread',
        'ordered_dishes',
        'bid',
        'orders',
        'dishes',
        'accounts',
        'restaurant',
    ]
    
    for table in tables_to_drop:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
