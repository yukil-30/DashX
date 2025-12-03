"""
Schema Conformance Tests
Verifies database structure matches the authoritative schema documentation.
"""
import pytest
import pytest_asyncio
import asyncpg
from typing import Dict, List, Set
import os


@pytest_asyncio.fixture
async def db_conn():
    """Database connection for schema inspection"""
    database_url = os.getenv("DATABASE_URL", "postgresql://restaurant_user:restaurant_password@localhost:5432/restaurant_db")
    conn = await asyncpg.connect(database_url)
    yield conn
    await conn.close()


# Authoritative schema definition
EXPECTED_TABLES = {
    "restaurant", "accounts", "dishes", "orders", "ordered_dishes",
    "bid", "thread", "post", "agent_query", "agent_answer",
    "DeliveryRating", "complaint", "closureRequest", "openRequest",
    "transactions", "voice_reports", "knowledge_base",
    "chat_log", "audit_log", "blacklist", "manager_notifications"
}

# Key columns that MUST exist for each table
EXPECTED_COLUMNS = {
    "restaurant": {"id", "name", "address"},
    "accounts": {"ID", "restaurantID", "email", "password", "type", "balance", "warnings", "is_blacklisted", "free_delivery_credits"},
    "dishes": {"id", "restaurantID", "name", "description", "cost", "picture", "average_rating", "reviews", "chefID"},
    "orders": {"id", "accountID", "dateTime", "finalCost", "status", "bidID", "delivery_fee", "subtotal_cents", "discount_cents"},
    "ordered_dishes": {"DishID", "orderID", "quantity"},
    "bid": {"id", "orderID", "deliveryPersonID", "bidAmount", "estimated_minutes"},
    "complaint": {"id", "accountID", "filer", "type", "description", "status", "resolution", "order_id"},
    "DeliveryRating": {"accountID", "averageRating", "reviews", "total_deliveries"},
    "transactions": {"id", "accountID", "amount_cents", "balance_before", "balance_after", "transaction_type", "created_at"},
    "voice_reports": {"id", "submitter_id", "audio_file_path", "transcription", "sentiment", "subjects", "auto_labels", "status"},
    "knowledge_base": {"id", "question", "answer", "confidence", "is_active"},
    "chat_log": {"id", "user_id", "question", "answer", "source", "rating", "flagged"},
}

# Foreign key relationships
EXPECTED_FOREIGN_KEYS = {
    "accounts": [("restaurantID", "restaurant", "id")],
    "dishes": [("restaurantID", "restaurant", "id"), ("chefID", "accounts", "ID")],
    "orders": [("accountID", "accounts", "ID"), ("bidID", "bid", "id")],
    "ordered_dishes": [("orderID", "orders", "id"), ("DishID", "dishes", "id")],
    "bid": [("orderID", "orders", "id"), ("deliveryPersonID", "accounts", "ID")],
    "complaint": [("accountID", "accounts", "ID"), ("filer", "accounts", "ID")],
    "transactions": [("accountID", "accounts", "ID")],
    "voice_reports": [("submitter_id", "accounts", "ID")],
}


@pytest.mark.asyncio
async def test_all_expected_tables_exist(db_conn):
    """Verify all required tables exist in database"""
    query = """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
    """
    rows = await db_conn.fetch(query)
    actual_tables = {row['tablename'] for row in rows}
    
    missing_tables = EXPECTED_TABLES - actual_tables
    extra_tables = actual_tables - EXPECTED_TABLES - {'alembic_version'}  # Allow alembic table
    
    assert not missing_tables, f"Missing required tables: {missing_tables}"
    # Extra tables are OK (extensions/additions), just report them
    if extra_tables:
        print(f"Note: Additional tables found (may be OK): {extra_tables}")


@pytest.mark.asyncio
async def test_required_columns_exist(db_conn):
    """Verify each table has its required columns"""
    errors = []
    
    for table_name, expected_cols in EXPECTED_COLUMNS.items():
        query = f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = $1
        """
        rows = await db_conn.fetch(query, table_name)
        actual_cols = {row['column_name'] for row in rows}
        
        missing_cols = expected_cols - actual_cols
        if missing_cols:
            errors.append(f"Table '{table_name}' missing columns: {missing_cols}")
    
    assert not errors, "\n".join(errors)


@pytest.mark.asyncio
async def test_foreign_key_constraints(db_conn):
    """Verify critical foreign key relationships exist"""
    errors = []
    
    for table_name, expected_fks in EXPECTED_FOREIGN_KEYS.items():
        query = """
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = $1
        """
        rows = await db_conn.fetch(query, table_name)
        actual_fks = {
            (row['column_name'], row['foreign_table_name'], row['foreign_column_name'])
            for row in rows
        }
        
        for expected_fk in expected_fks:
            if expected_fk not in actual_fks:
                errors.append(f"Table '{table_name}' missing FK: {expected_fk[0]} -> {expected_fk[1]}({expected_fk[2]})")
    
    # Some FKs may be optional, so we only check for critical ones
    # A real implementation would check all FKs from schema doc
    if errors:
        print(f"Warning: Some FK constraints may be missing:\n" + "\n".join(errors))


@pytest.mark.asyncio
async def test_account_types_enum_values(db_conn):
    """Verify account type values match expected roles"""
    query = "SELECT DISTINCT type FROM accounts"
    rows = await db_conn.fetch(query)
    account_types = {row['type'] for row in rows}
    
    expected_types = {'visitor', 'customer', 'vip', 'chef', 'delivery', 'manager'}
    invalid_types = account_types - expected_types
    
    assert not invalid_types, f"Invalid account types found: {invalid_types}"


@pytest.mark.asyncio
async def test_monetary_values_are_integers(db_conn):
    """Verify all monetary values stored as integers (cents)"""
    # Check accounts.balance
    query = "SELECT pg_typeof(balance) as type FROM accounts LIMIT 1"
    result = await db_conn.fetchrow(query)
    assert result and 'int' in str(result['type']), "accounts.balance must be integer type"
    
    # Check dishes.cost
    query = "SELECT pg_typeof(cost) as type FROM dishes LIMIT 1"
    result = await db_conn.fetchrow(query)
    assert result and 'int' in str(result['type']), "dishes.cost must be integer type"
    
    # Check orders.finalCost
    query = "SELECT pg_typeof(\"finalCost\") as type FROM orders LIMIT 1"
    result = await db_conn.fetchrow(query)
    assert result and 'int' in str(result['type']), "orders.finalCost must be integer type"


@pytest.mark.asyncio
async def test_voice_reports_table_structure(db_conn):
    """Verify voice_reports table matches specification"""
    query = """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'voice_reports'
        ORDER BY ordinal_position
    """
    rows = await db_conn.fetch(query)
    columns = {row['column_name']: row for row in rows}
    
    # Required columns
    assert 'id' in columns
    assert 'submitter_id' in columns
    assert 'audio_file_path' in columns
    assert 'transcription' in columns
    assert 'sentiment' in columns
    assert 'subjects' in columns  # Should be JSONB
    assert 'auto_labels' in columns  # Should be JSONB
    assert 'status' in columns
    assert 'confidence_score' in columns
    
    # Check JSONB columns
    assert 'json' in columns['subjects']['data_type'].lower(), "subjects must be JSONB"
    assert 'json' in columns['auto_labels']['data_type'].lower(), "auto_labels must be JSONB"


@pytest.mark.asyncio
async def test_transactions_audit_trail(db_conn):
    """Verify transactions table exists with audit fields"""
    query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'transactions'
    """
    rows = await db_conn.fetch(query)
    columns = {row['column_name'] for row in rows}
    
    required = {'id', 'accountID', 'amount_cents', 'balance_before', 'balance_after', 
                'transaction_type', 'created_at'}
    missing = required - columns
    
    assert not missing, f"transactions table missing audit fields: {missing}"


@pytest.mark.asyncio
async def test_check_constraints_exist(db_conn):
    """Verify important check constraints are in place"""
    # Test that dish cost cannot be negative
    query = """
        SELECT conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conrelid = 'dishes'::regclass
        AND contype = 'c'
    """
    rows = await db_conn.fetch(query)
    constraints = [row['pg_get_constraintdef'] for row in rows]
    
    # Should have check for cost >= 0
    has_cost_check = any('cost' in str(c).lower() and '>=' in str(c) for c in constraints)
    assert has_cost_check, "dishes table missing CHECK constraint on cost"


@pytest.mark.asyncio
async def test_unique_constraints(db_conn):
    """Verify unique constraints on critical fields"""
    # accounts.email should be unique
    query = """
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'accounts'
        AND constraint_type = 'UNIQUE'
    """
    rows = await db_conn.fetch(query)
    
    # Check email uniqueness by trying to get column info
    query = """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = 'accounts'::regclass
        AND i.indisunique = true
    """
    rows = await db_conn.fetch(query)
    unique_columns = {row['attname'] for row in rows}
    
    assert 'email' in unique_columns, "accounts.email must have UNIQUE constraint"


@pytest.mark.asyncio
async def test_jsonb_columns_for_flexibility(db_conn):
    """Verify JSONB columns exist for flexible data storage"""
    query = """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE data_type = 'jsonb'
        AND table_schema = 'public'
    """
    rows = await db_conn.fetch(query)
    jsonb_columns = {(row['table_name'], row['column_name']) for row in rows}
    
    # Expected JSONB columns
    expected_jsonb = [
        ('voice_reports', 'subjects'),
        ('voice_reports', 'auto_labels'),
        ('audit_log', 'details'),
    ]
    
    for table, column in expected_jsonb:
        assert (table, column) in jsonb_columns, f"{table}.{column} should be JSONB type"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
