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


@pytest.fixture(scope="module")
def db_engine():
    """Create database engine for tests."""
    engine = create_engine(DATABASE_URL)
    return engine


@pytest.fixture(scope="module")
def db_session(db_engine):
    """Create a database session for tests."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


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


class TestTableExistence:
    """Test that all required tables exist - authoritative schema."""
    
    # Tables from the authoritative schema
    REQUIRED_TABLES = [
        'restaurant',
        'accounts', 
        'dishes',
        'orders',
        'ordered_dishes',
        'bid',
        'complaint',
        'thread',
        'post',
        'agent_query',
        'agent_answer',
        'DeliveryRating',
        'openRequest',
        'closureRequest',
    ]
    
    def test_all_tables_exist(self, db_session):
        """Verify all required tables are created."""
        result = db_session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """))
        existing_tables = {row[0] for row in result}
        
        for table in self.REQUIRED_TABLES:
            assert table in existing_tables, f"Table '{table}' does not exist"


class TestUniqueConstraints:
    """Test unique constraints."""
    
    def test_duplicate_email_fails(self, transaction_session):
        """Inserting duplicate email should fail."""
        # First insert should succeed
        transaction_session.execute(text("""
            INSERT INTO accounts (email, password, type)
            VALUES ('unique_test@example.com', 'hash123', 'customer')
        """))
        
        # Second insert with same email should fail
        with pytest.raises(IntegrityError) as excinfo:
            transaction_session.execute(text("""
                INSERT INTO accounts (email, password, type)
                VALUES ('unique_test@example.com', 'hash456', 'customer')
            """))
            transaction_session.commit()
        
        assert 'duplicate key' in str(excinfo.value).lower() or \
               'unique constraint' in str(excinfo.value).lower()


class TestForeignKeyConstraints:
    """Test foreign key constraints."""
    
    def test_order_with_nonexistent_account_fails(self, transaction_session):
        """Creating order for non-existent customer should fail."""
        with pytest.raises(IntegrityError) as excinfo:
            transaction_session.execute(text("""
                INSERT INTO orders ("accountID", "dateTime", "finalCost", status)
                VALUES (999999, NOW(), 1000, 'pending')
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
            INSERT INTO dishes (id, "restaurantID", name, cost)
            VALUES (9999, 9991, 'Test Dish', 999)
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
            INSERT INTO dishes (id, "restaurantID", name, cost)
            VALUES (9993, 9993, 'Cascade Test Dish', 999)
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
                INSERT INTO dishes ("restaurantID", name, cost)
                VALUES (9994, 'Negative Cost Dish', -100)
            """))
            transaction_session.commit()
        
        assert 'check' in str(excinfo.value).lower() or \
               'violates' in str(excinfo.value).lower()
    
    def test_zero_quantity_fails(self, transaction_session):
        """Ordered dish quantity must be positive."""
        # Setup
        transaction_session.execute(text("""
            INSERT INTO restaurant (id, name, address) 
            VALUES (9995, 'Qty Test Restaurant', 'Test Address')
            ON CONFLICT (id) DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO accounts ("ID", email, password, type)
            VALUES (9996, 'qty_test@test.com', 'hash', 'customer')
            ON CONFLICT ("ID") DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO dishes (id, "restaurantID", name, cost)
            VALUES (9996, 9995, 'Qty Test Dish', 999)
            ON CONFLICT (id) DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO orders (id, "accountID", "dateTime", "finalCost", status)
            VALUES (9996, 9996, NOW(), 999, 'pending')
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
    
    def test_accounts_count(self, db_session):
        """Verify expected number of seeded accounts."""
        result = db_session.execute(text("SELECT COUNT(*) FROM accounts"))
        count = result.scalar()
        assert count >= 11, f"Expected at least 11 accounts, got {count}"
    
    def test_dishes_count(self, db_session):
        """Verify expected number of seeded dishes."""
        result = db_session.execute(text("SELECT COUNT(*) FROM dishes"))
        count = result.scalar()
        assert count >= 5, f"Expected at least 5 dishes, got {count}"
    
    def test_orders_count(self, db_session):
        """Verify expected number of seeded orders."""
        result = db_session.execute(text("SELECT COUNT(*) FROM orders"))
        count = result.scalar()
        assert count >= 5, f"Expected at least 5 orders, got {count}"
    
    def test_bids_count(self, db_session):
        """Verify expected number of seeded bids."""
        result = db_session.execute(text("SELECT COUNT(*) FROM bid"))
        count = result.scalar()
        assert count >= 6, f"Expected at least 6 bids, got {count}"
    
    def test_vip_exists(self, db_session):
        """Verify at least one VIP customer exists."""
        result = db_session.execute(text(
            "SELECT COUNT(*) FROM accounts WHERE type = 'vip'"
        ))
        count = result.scalar()
        assert count >= 1, "No VIP customers found"
    
    def test_no_high_warning_users(self, db_session):
        """Verify no users have 3+ warnings in seed data."""
        result = db_session.execute(text(
            "SELECT * FROM accounts WHERE warnings >= 3"
        ))
        rows = result.fetchall()
        assert len(rows) == 0, f"Found {len(rows)} users with 3+ warnings"


class TestComplexQueries:
    """Test complex queries on seeded data."""
    
    def test_top_5_popular_dishes(self, db_session):
        """Query for top 5 most popular dishes by order count."""
        result = db_session.execute(text("""
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
        
        # Verify ordering (descending by order_count)
        for i in range(1, len(rows)):
            assert rows[i-1][2] >= rows[i][2], "Results not properly ordered"
    
    def test_top_5_rated_dishes(self, db_session):
        """Query for top 5 highest-rated dishes."""
        result = db_session.execute(text("""
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
        
        # Verify ordering (descending by rating)
        for i in range(1, len(rows)):
            assert rows[i-1][2] >= rows[i][2], "Results not properly ordered by rating"
    
    def test_customer_order_history(self, db_session):
        """Query orders for a specific customer."""
        # Get VIP customer's orders
        result = db_session.execute(text("""
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
            INSERT INTO accounts ("ID", email, password, type)
            VALUES 
                (9960, 'complaint_subject@test.com', 'hash', 'delivery'),
                (9961, 'complaint_reporter@test.com', 'hash', 'customer')
            ON CONFLICT ("ID") DO NOTHING
        """))
        
        # File a complaint
        transaction_session.execute(text("""
            INSERT INTO complaint (id, "accountID", type, description, filer)
            VALUES (9960, 9960, 'complaint', 'Test complaint', 9961)
        """))
        
        # Verify complaint was inserted
        result = transaction_session.execute(text(
            "SELECT type, description FROM complaint WHERE id = 9960"
        ))
        row = result.fetchone()
        assert row[0] == 'complaint'
        assert row[1] == 'Test complaint'
