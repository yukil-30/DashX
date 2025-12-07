"""
DashX Schema Integrity Tests - Authoritative Schema

This module tests database schema constraints, foreign keys, and data integrity.
Tests are designed to verify:
1. Foreign key constraints work correctly
2. Unique constraints prevent duplicates
3. Check constraints enforce valid data
4. Transactions maintain consistency

Run with: pytest backend/tests/test_schema.py -v
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, DataError
import os


# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://restaurant_user:restaurant_password@localhost:5432/restaurant_db"
)


@pytest.fixture(scope="function")
def transaction_session(db_engine):
    """Create a session with transaction rollback for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


from sqlalchemy import inspect

class TestTableExistence:
    """Test that all expected tables exist in the database."""
    
    def test_all_tables_exist(self, db_engine):
        """Verify all tables from schema are present."""
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            'restaurant', 'accounts', 'dishes', 'orders', 
            'ordered_dishes', 'bid', 'thread', 'post',
            'agent_query', 'agent_answer', 'DeliveryRating',
            'complaint', 'closureRequest', 'openRequest',
            'transactions', 'audit_log', 'blacklist',
            'manager_notifications', 'knowledge_base',
            'chat_log', 'voice_reports'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} missing from database"



class TestUniqueConstraints:
    """Test unique constraints."""
    
    def test_duplicate_email_fails(self, transaction_session):
        """Email must be unique across accounts."""
        # Insert first account
        transaction_session.execute(text("""
            INSERT INTO accounts (email, password, type, warnings, balance, free_delivery_credits, completed_orders_count, times_demoted, is_fired, is_blacklisted, total_spent_cents, unresolved_complaints_count, is_vip)
            VALUES ('unique_test@example.com', 'hash123', 'customer', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        """))
        
        # Try to insert second account with same email
        with pytest.raises(IntegrityError):
            transaction_session.execute(text("""
                INSERT INTO accounts (email, password, type, warnings, balance, free_delivery_credits, completed_orders_count, times_demoted, is_fired, is_blacklisted, total_spent_cents, unresolved_complaints_count, is_vip)
                VALUES ('unique_test@example.com', 'hash456', 'delivery', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            """))


class TestForeignKeyConstraints:
    """Test foreign key constraints."""
    
    def test_order_with_nonexistent_account_fails(self, transaction_session):
        """Creating order for non-existent customer should fail."""
        from datetime import datetime
        now = datetime.now().isoformat()
        
        with pytest.raises(IntegrityError) as excinfo:
            transaction_session.execute(text(f"""
                INSERT INTO orders ("accountID", "dateTime", "finalCost", status, delivery_fee, subtotal_cents, discount_cents, free_delivery_used)
                VALUES (999999, '{now}', 1000, 'pending', 0, 0, 0, 0)
            """))
            transaction_session.commit()
        
        assert 'foreign key' in str(excinfo.value).lower() or \
               'violates' in str(excinfo.value).lower()
    
    def test_ordered_dish_with_nonexistent_order_fails(self, transaction_session):
        """Adding dish to non-existent order should fail."""
        # Setup: create restaurant and dish
        transaction_session.execute(text("""
            INSERT INTO restaurant (id, name, address)
            VALUES (9991, 'FK Test Restaurant 2', 'Test Address')
            ON CONFLICT (id) DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO dishes (id, "restaurantID", name, cost, reviews)
            VALUES (9999, 9991, 'Test Dish', 999, 0)
            ON CONFLICT (id) DO NOTHING
        """))
        
        with pytest.raises(IntegrityError) as excinfo:
            transaction_session.execute(text("""
                INSERT INTO ordered_dishes ("DishID", "orderID", quantity)
                VALUES (9999, 999999, 1)
            """))

            transaction_session.commit()
        
        assert 'foreign key' in str(excinfo.value).lower() or \
               'violates' in str(excinfo.value).lower()
    
    def test_cascade_delete_on_restaurant_dishes(self, transaction_session):
        """Deleting restaurant should cascade delete its dishes."""
        # Create restaurant and dish
        transaction_session.execute(text("""
            INSERT INTO restaurant (id, name, address)
            VALUES (9993, 'Cascade Test Restaurant', 'Test Address')
        """))
        transaction_session.execute(text("""
            INSERT INTO dishes (id, "restaurantID", name, cost, reviews)
            VALUES (9993, 9993, 'Cascade Test Dish', 999, 0)
        """))
        # Verify dish exists
        result = transaction_session.execute(text(
            """SELECT COUNT(*) FROM dishes WHERE "restaurantID" = 9993"""
        ))
        assert result.scalar() == 1
        
        # Delete restaurant
        transaction_session.execute(text("DELETE FROM restaurant WHERE id = 9993"))
        
        # Verify dish was cascade deleted
        result = transaction_session.execute(text(
            "SELECT COUNT(*) FROM dishes WHERE id = 9993"
        ))
        assert result.scalar() == 0


class TestCheckConstraints:
    """Test CHECK constraints."""
    
    def test_negative_cost_fails(self, transaction_session):
        """Dish cost cannot be negative."""
        transaction_session.execute(text("""
            INSERT INTO restaurant (id, name, address)
            VALUES (9994, 'Check Test Restaurant', 'Test Address')
            ON CONFLICT (id) DO NOTHING
        """))
    
        with pytest.raises(IntegrityError) as excinfo:
            transaction_session.execute(text("""
                INSERT INTO dishes ("restaurantID", name, cost, reviews)
                VALUES (9994, 'Negative Cost Dish', -100, 0)
            """))
            transaction_session.commit()
        
        assert 'check' in str(excinfo.value).lower() or \
               'violates' in str(excinfo.value).lower() or \
               'constraint failed' in str(excinfo.value).lower()
    
    def test_zero_quantity_fails(self, transaction_session):
        """Ordered dish quantity must be positive."""
        # Setup
        transaction_session.execute(text("""
            INSERT INTO restaurant (id, name, address)
            VALUES (9995, 'Qty Test Restaurant', 'Test Address')
            ON CONFLICT (id) DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO accounts ("ID", email, password, type, warnings, balance, free_delivery_credits, completed_orders_count, times_demoted, is_fired, is_blacklisted, total_spent_cents, unresolved_complaints_count, is_vip)
            VALUES (9996, 'qty_test@test.com', 'hash', 'customer', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            ON CONFLICT ("ID") DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO dishes (id, "restaurantID", name, cost, reviews)
            VALUES (9996, 9995, 'Qty Test Dish', 999, 0)
            ON CONFLICT (id) DO NOTHING
        """))
        
        # Use current timestamp for SQLite compatibility
        from datetime import datetime
        now = datetime.now().isoformat()
        
        transaction_session.execute(text(f"""
            INSERT INTO orders (id, "accountID", "dateTime", "finalCost", status, delivery_fee, subtotal_cents, discount_cents, free_delivery_used)
            VALUES (9996, 9996, '{now}', 999, 'pending', 0, 0, 0, 0)
            ON CONFLICT (id) DO NOTHING
        """))
        
        with pytest.raises(IntegrityError):
            transaction_session.execute(text("""
                INSERT INTO ordered_dishes ("DishID", "orderID", quantity)
                VALUES (9996, 9996, 0)
            """))
            transaction_session.commit()


class TestSeedDataIntegrity:
    """Test seed data was loaded correctly."""
    
    def test_accounts_count(self, seed_db):
        """Verify expected number of seeded accounts."""
        result = seed_db.execute(text("SELECT COUNT(*) FROM accounts"))
        count = result.scalar()
        assert count >= 11, f"Expected at least 11 accounts, got {count}"
    
    def test_dishes_count(self, seed_db):
        """Verify expected number of seeded dishes."""
        result = seed_db.execute(text("SELECT COUNT(*) FROM dishes"))
        count = result.scalar()
        assert count >= 5, f"Expected at least 5 dishes, got {count}"
    
    def test_orders_count(self, seed_db):
        """Verify expected number of seeded orders."""
        result = seed_db.execute(text("SELECT COUNT(*) FROM orders"))
        count = result.scalar()
        assert count >= 5, f"Expected at least 5 orders, got {count}"
    
    def test_bids_count(self, seed_db):
        """Verify expected number of seeded bids."""
        result = seed_db.execute(text("SELECT COUNT(*) FROM bid"))
        count = result.scalar()
        assert count >= 6, f"Expected at least 6 bids, got {count}"
    
    def test_vip_exists(self, seed_db):
        """Verify at least one VIP customer exists."""
        result = seed_db.execute(text(
            "SELECT COUNT(*) FROM accounts WHERE type = 'vip'"
        ))
        count = result.scalar()
        assert count >= 1, "No VIP customers found"
    
    def test_no_high_warning_users(self, seed_db):
        """Verify no users have 3+ warnings in seed data."""
        result = seed_db.execute(text(
            "SELECT * FROM accounts WHERE warnings >= 3"
        ))
        rows = result.fetchall()
        assert len(rows) == 0, f"Found {len(rows)} users with 3+ warnings"


class TestComplexQueries:
    """Test complex queries on seeded data."""
    
    def test_top_5_popular_dishes(self, seed_db):
        """Query for top 5 most popular dishes by order count."""
        result = seed_db.execute(text("""
            SELECT 
                d.id,
                d.name,
                COALESCE(SUM(od.quantity), 0) as order_count
            FROM dishes d
            LEFT JOIN ordered_dishes od ON d.id = od."DishID"
            GROUP BY d.id
            ORDER BY order_count DESC
            LIMIT 5
        """))
        rows = result.fetchall()
        
        assert len(rows) <= 5
        assert len(rows) > 0, "No dishes found"
    
    def test_top_5_rated_dishes(self, seed_db):
        """Query for top 5 highest-rated dishes."""
        result = seed_db.execute(text("""
            SELECT 
                id,
                name,
                average_rating,
                reviews
            FROM dishes
            ORDER BY average_rating DESC, reviews DESC
            LIMIT 5
        """))
        rows = result.fetchall()
        
        assert len(rows) <= 5
        assert len(rows) > 0, "No dishes found"
    
    def test_customer_order_history(self, seed_db):
        """Query orders for a specific customer."""
        # Get VIP customer's orders
        result = seed_db.execute(text("""
            SELECT 
                o.id,
                o."dateTime",
                o."finalCost",
                o.status,
                a.email
            FROM orders o
            JOIN accounts a ON o."accountID" = a."ID"
            WHERE a.type = 'vip'
            ORDER BY o."dateTime" DESC
        """))
        rows = result.fetchall()
        
        assert len(rows) >= 1, "VIP customer should have at least one order"


class TestComplaintFlow:
    """Test complaint resolution workflow."""
    
    def test_complaint_insert(self, transaction_session):
        """Test inserting a complaint."""
        # Setup accounts
        transaction_session.execute(text("""
            INSERT INTO accounts ("ID", email, password, type, warnings, balance, free_delivery_credits, completed_orders_count, times_demoted, is_fired, is_blacklisted, total_spent_cents, unresolved_complaints_count, is_vip)
            VALUES
                (9960, 'complaint_subject@test.com', 'hash', 'delivery', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                (9961, 'complaint_reporter@test.com', 'hash', 'customer', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            ON CONFLICT ("ID") DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO complaint (id, "accountID", type, description, filer, status)
            VALUES (9960, 9960, 'complaint', 'Test complaint', 9961, 'pending')
        """))
        
        # Verify complaint was inserted
        result = transaction_session.execute(text(
            "SELECT type, description FROM complaint WHERE id = 9960"
        ))
        row = result.fetchone()
        assert row[0] == 'complaint'
        assert row[1] == 'Test complaint'
