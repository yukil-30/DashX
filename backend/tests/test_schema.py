"""
DashX Schema Integrity Tests

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
    """Test that all required tables exist."""
    
    REQUIRED_TABLES = [
        'restaurant',
        'accounts', 
        'dishes',
        'orders',
        'ordered_dishes',
        'bids',
        'complaints',
        'threads',
        'posts',
        'agent_queries',
        'agent_answers',
        'delivery_ratings',
        'dish_reviews',
        'open_requests',
        'closure_requests',
        'transactions',
        'vip_history',
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


class TestEnumTypes:
    """Test that ENUM types are created correctly."""
    
    def test_account_type_enum_exists(self, db_session):
        """Verify account_type enum is created."""
        result = db_session.execute(text("""
            SELECT enumlabel FROM pg_enum 
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
            WHERE pg_type.typname = 'account_type'
            ORDER BY enumsortorder
        """))
        labels = [row[0] for row in result]
        
        expected = ['visitor', 'customer', 'vip', 'chef', 'delivery', 'manager']
        assert labels == expected, f"account_type enum values: {labels}"
    
    def test_order_status_enum_exists(self, db_session):
        """Verify order_status enum is created."""
        result = db_session.execute(text("""
            SELECT enumlabel FROM pg_enum 
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
            WHERE pg_type.typname = 'order_status'
            ORDER BY enumsortorder
        """))
        labels = [row[0] for row in result]
        
        expected = ['pending', 'confirmed', 'preparing', 'ready', 
                    'out_for_delivery', 'delivered', 'cancelled', 'refunded']
        assert labels == expected, f"order_status enum values: {labels}"


class TestUniqueConstraints:
    """Test unique constraints."""
    
    def test_duplicate_email_fails(self, transaction_session):
        """Inserting duplicate email should fail."""
        # First insert should succeed
        transaction_session.execute(text("""
            INSERT INTO accounts (email, password_hash, account_type)
            VALUES ('unique_test@example.com', 'hash123', 'customer')
        """))
        
        # Second insert with same email should fail
        with pytest.raises(IntegrityError) as excinfo:
            transaction_session.execute(text("""
                INSERT INTO accounts (email, password_hash, account_type)
                VALUES ('unique_test@example.com', 'hash456', 'customer')
            """))
            transaction_session.commit()
        
        assert 'duplicate key' in str(excinfo.value).lower() or \
               'unique constraint' in str(excinfo.value).lower()
    
    def test_duplicate_bid_per_order_fails(self, transaction_session):
        """Same delivery person can't bid twice on same order."""
        # Setup: create required parent records
        transaction_session.execute(text("""
            INSERT INTO restaurant (id, name, address) 
            VALUES (9999, 'Test Restaurant', 'Test Address')
        """))
        transaction_session.execute(text("""
            INSERT INTO accounts (id, email, password_hash, account_type) 
            VALUES (9999, 'test_customer_99@test.com', 'hash', 'customer'),
                   (9998, 'test_delivery_99@test.com', 'hash', 'delivery')
        """))
        transaction_session.execute(text("""
            INSERT INTO orders (id, account_id, restaurant_id, final_cost, subtotal, status)
            VALUES (9999, 9999, 9999, 1000, 1000, 'pending')
        """))
        
        # First bid should succeed
        transaction_session.execute(text("""
            INSERT INTO bids (order_id, delivery_person_id, bid_amount)
            VALUES (9999, 9998, 500)
        """))
        
        # Second bid from same person should fail
        with pytest.raises(IntegrityError):
            transaction_session.execute(text("""
                INSERT INTO bids (order_id, delivery_person_id, bid_amount)
                VALUES (9999, 9998, 600)
            """))
            transaction_session.commit()


class TestForeignKeyConstraints:
    """Test foreign key constraints."""
    
    def test_order_with_nonexistent_account_fails(self, transaction_session):
        """Creating order for non-existent customer should fail."""
        # Ensure restaurant exists
        transaction_session.execute(text("""
            INSERT INTO restaurant (id, name, address) 
            VALUES (9990, 'FK Test Restaurant', 'FK Test Address')
            ON CONFLICT (id) DO NOTHING
        """))
        
        with pytest.raises(IntegrityError) as excinfo:
            transaction_session.execute(text("""
                INSERT INTO orders (account_id, restaurant_id, final_cost, subtotal, status)
                VALUES (999999, 9990, 1000, 1000, 'pending')
            """))
            transaction_session.commit()
        
        assert 'foreign key' in str(excinfo.value).lower() or \
               'violates' in str(excinfo.value).lower()
    
    def test_ordered_dish_with_nonexistent_order_fails(self, transaction_session):
        """Adding dish to non-existent order should fail."""
        # Setup: create dish
        transaction_session.execute(text("""
            INSERT INTO restaurant (id, name, address) 
            VALUES (9991, 'FK Test Restaurant 2', 'Test Address')
            ON CONFLICT (id) DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO dishes (id, restaurant_id, name, price)
            VALUES (9999, 9991, 'Test Dish', 999)
            ON CONFLICT (id) DO NOTHING
        """))
        
        with pytest.raises(IntegrityError) as excinfo:
            transaction_session.execute(text("""
                INSERT INTO ordered_dishes (order_id, dish_id, quantity, unit_price)
                VALUES (999999, 9999, 1, 999)
            """))
            transaction_session.commit()
        
        assert 'foreign key' in str(excinfo.value).lower() or \
               'violates' in str(excinfo.value).lower()
    
    def test_ordered_dish_with_nonexistent_dish_fails(self, transaction_session):
        """Adding non-existent dish to order should fail."""
        # Setup: create order
        transaction_session.execute(text("""
            INSERT INTO restaurant (id, name, address) 
            VALUES (9992, 'FK Test Restaurant 3', 'Test Address')
            ON CONFLICT (id) DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO accounts (id, email, password_hash, account_type)
            VALUES (9997, 'fk_test_customer@test.com', 'hash', 'customer')
            ON CONFLICT (id) DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO orders (id, account_id, restaurant_id, final_cost, subtotal, status)
            VALUES (9998, 9997, 9992, 1000, 1000, 'pending')
            ON CONFLICT (id) DO NOTHING
        """))
        
        with pytest.raises(IntegrityError) as excinfo:
            transaction_session.execute(text("""
                INSERT INTO ordered_dishes (order_id, dish_id, quantity, unit_price)
                VALUES (9998, 999999, 1, 999)
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
            INSERT INTO dishes (id, restaurant_id, name, price)
            VALUES (9993, 9993, 'Cascade Test Dish', 999)
        """))
        
        # Verify dish exists
        result = transaction_session.execute(text(
            "SELECT COUNT(*) FROM dishes WHERE restaurant_id = 9993"
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
    
    def test_negative_price_fails(self, transaction_session):
        """Dish price cannot be negative."""
        transaction_session.execute(text("""
            INSERT INTO restaurant (id, name, address) 
            VALUES (9994, 'Check Test Restaurant', 'Test Address')
            ON CONFLICT (id) DO NOTHING
        """))
        
        with pytest.raises(IntegrityError) as excinfo:
            transaction_session.execute(text("""
                INSERT INTO dishes (restaurant_id, name, price)
                VALUES (9994, 'Negative Price Dish', -100)
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
            INSERT INTO accounts (id, email, password_hash, account_type)
            VALUES (9996, 'qty_test@test.com', 'hash', 'customer')
            ON CONFLICT (id) DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO dishes (id, restaurant_id, name, price)
            VALUES (9996, 9995, 'Qty Test Dish', 999)
            ON CONFLICT (id) DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO orders (id, account_id, restaurant_id, final_cost, subtotal, status)
            VALUES (9996, 9996, 9995, 999, 999, 'pending')
            ON CONFLICT (id) DO NOTHING
        """))
        
        with pytest.raises(IntegrityError):
            transaction_session.execute(text("""
                INSERT INTO ordered_dishes (order_id, dish_id, quantity, unit_price)
                VALUES (9996, 9996, 0, 999)
            """))
            transaction_session.commit()
    
    def test_rating_out_of_range_fails(self, transaction_session):
        """Rating must be between 1 and 5."""
        # Setup
        transaction_session.execute(text("""
            INSERT INTO restaurant (id, name, address) 
            VALUES (9980, 'Rating Test Restaurant', 'Test Address')
            ON CONFLICT (id) DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO accounts (id, email, password_hash, account_type)
            VALUES 
                (9980, 'rating_cust@test.com', 'hash', 'customer'),
                (9981, 'rating_deliv@test.com', 'hash', 'delivery')
            ON CONFLICT (id) DO NOTHING
        """))
        transaction_session.execute(text("""
            INSERT INTO orders (id, account_id, restaurant_id, final_cost, subtotal, status)
            VALUES (9980, 9980, 9980, 1000, 1000, 'delivered')
            ON CONFLICT (id) DO NOTHING
        """))
        
        # Rating of 6 should fail
        with pytest.raises(IntegrityError):
            transaction_session.execute(text("""
                INSERT INTO delivery_ratings (delivery_person_id, order_id, rater_id, rating)
                VALUES (9981, 9980, 9980, 6)
            """))
            transaction_session.commit()
    
    def test_self_complaint_fails(self, transaction_session):
        """Cannot file complaint about yourself."""
        transaction_session.execute(text("""
            INSERT INTO accounts (id, email, password_hash, account_type)
            VALUES (9970, 'self_complaint@test.com', 'hash', 'customer')
            ON CONFLICT (id) DO NOTHING
        """))
        
        with pytest.raises(IntegrityError):
            transaction_session.execute(text("""
                INSERT INTO complaints (about_account_id, reporter_account_id, feedback_type, description)
                VALUES (9970, 9970, 'complaint', 'Trying to complain about myself')
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
        result = db_session.execute(text("SELECT COUNT(*) FROM bids"))
        count = result.scalar()
        assert count >= 6, f"Expected at least 6 bids, got {count}"
    
    def test_vip_exists(self, db_session):
        """Verify at least one VIP customer exists."""
        result = db_session.execute(text(
            "SELECT COUNT(*) FROM accounts WHERE account_type = 'vip'"
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
            LEFT JOIN ordered_dishes od ON d.id = od.dish_id
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
                review_count
            FROM dishes
            ORDER BY average_rating DESC, review_count DESC
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
                o.order_datetime,
                o.final_cost,
                o.status,
                a.first_name
            FROM orders o
            JOIN accounts a ON o.account_id = a.id
            WHERE a.account_type = 'vip'
            ORDER BY o.order_datetime DESC
        """))
        rows = result.fetchall()
        
        assert len(rows) >= 1, "VIP customer should have at least one order"


class TestComplaintFlow:
    """Test complaint resolution workflow."""
    
    def test_complaint_resolution_flow(self, transaction_session):
        """Test inserting and resolving a complaint."""
        # Setup accounts
        transaction_session.execute(text("""
            INSERT INTO accounts (id, email, password_hash, account_type)
            VALUES 
                (9960, 'complaint_subject@test.com', 'hash', 'delivery'),
                (9961, 'complaint_reporter@test.com', 'hash', 'customer'),
                (9962, 'complaint_manager@test.com', 'hash', 'manager')
            ON CONFLICT (id) DO NOTHING
        """))
        
        # File a complaint
        transaction_session.execute(text("""
            INSERT INTO complaints (id, about_account_id, reporter_account_id, feedback_type, description)
            VALUES (9960, 9960, 9961, 'complaint', 'Test complaint for resolution flow')
        """))
        
        # Verify complaint is unresolved
        result = transaction_session.execute(text(
            "SELECT is_resolved FROM complaints WHERE id = 9960"
        ))
        assert result.scalar() == False
        
        # Resolve the complaint
        transaction_session.execute(text("""
            UPDATE complaints 
            SET is_resolved = TRUE,
                manager_decision = 'Warning issued',
                resolved_by_id = 9962,
                resolved_at = NOW()
            WHERE id = 9960
        """))
        
        # Verify complaint is now resolved
        result = transaction_session.execute(text("""
            SELECT is_resolved, manager_decision, resolved_by_id
            FROM complaints WHERE id = 9960
        """))
        row = result.fetchone()
        assert row[0] == True, "Complaint should be resolved"
        assert row[1] == 'Warning issued', "Manager decision should be set"
        assert row[2] == 9962, "Resolved by should be manager ID"


class TestTransactionAudit:
    """Test transaction audit trail."""
    
    def test_transaction_balance_tracking(self, transaction_session):
        """Verify transactions track balance changes correctly."""
        # Setup account
        transaction_session.execute(text("""
            INSERT INTO accounts (id, email, password_hash, account_type, balance)
            VALUES (9950, 'transaction_test@test.com', 'hash', 'customer', 0)
            ON CONFLICT (id) DO NOTHING
        """))
        
        # Record deposit
        transaction_session.execute(text("""
            INSERT INTO transactions (account_id, transaction_type, amount, balance_before, balance_after, description)
            VALUES (9950, 'deposit', 10000, 0, 10000, 'Test deposit')
        """))
        
        # Record payment
        transaction_session.execute(text("""
            INSERT INTO transactions (account_id, transaction_type, amount, balance_before, balance_after, description)
            VALUES (9950, 'order_payment', -5000, 10000, 5000, 'Test payment')
        """))
        
        # Verify transaction history
        result = transaction_session.execute(text("""
            SELECT transaction_type, amount, balance_before, balance_after
            FROM transactions 
            WHERE account_id = 9950 
            ORDER BY created_at
        """))
        rows = result.fetchall()
        
        assert len(rows) == 2
        
        # First transaction: deposit
        assert rows[0][0] == 'deposit'
        assert rows[0][1] == 10000
        assert rows[0][2] == 0  # balance_before
        assert rows[0][3] == 10000  # balance_after
        
        # Second transaction: payment
        assert rows[1][0] == 'order_payment'
        assert rows[1][1] == -5000
        assert rows[1][2] == 10000  # balance_before
        assert rows[1][3] == 5000  # balance_after
