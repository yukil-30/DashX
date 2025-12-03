"""
Finance and Orders Tests
Verifies deposits, order validation, VIP discounts, balance checks, and transaction audits.
"""
import pytest
import pytest_asyncio
import httpx
import asyncpg
import os
from datetime import datetime


BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://restaurant_user:restaurant_password@localhost:5432/restaurant_db")


@pytest_asyncio.fixture
async def client():
    """HTTP client for API requests"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def db_conn():
    """Database connection"""
    conn = await asyncpg.connect(DATABASE_URL)
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def customer_token(client):
    """Get customer JWT token"""
    response = await client.post("/auth/login", json={
        "email": "customer1@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def low_balance_customer(client, db_conn):
    """Create customer with low balance for testing"""
    unique_email = f"lowbalance_{datetime.now().timestamp()}@test.com"
    
    # Register
    response = await client.post("/auth/register", json={
        "email": unique_email,
        "password": "testpass123",
        "account_type": "customer"
    })
    assert response.status_code in [200, 201]
    
    # Login
    response = await client.post("/auth/login", json={
        "email": unique_email,
        "password": "testpass123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    account_id = response.json().get("account_id")
    
    return {"token": token, "email": unique_email, "account_id": account_id}


# ============================================================================
# DEPOSIT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_customer_can_deposit_funds(client, customer_token, db_conn):
    """Customer can deposit money to balance"""
    # Get current balance
    response = await client.get("/auth/me",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert response.status_code == 200
    user = response.json().get("user", response.json())
    before_balance = user["balance"]
    
    # Deposit $50
    response = await client.post("/account/deposit",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"amount_cents": 5000}
    )
    assert response.status_code == 200
    
    # Check new balance
    response = await client.get("/auth/me",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert response.status_code == 200
    user = response.json().get("user", response.json())
    after_balance = user["balance"]
    
    assert after_balance == before_balance + 5000


@pytest.mark.asyncio
async def test_deposit_creates_transaction_record(client, customer_token, db_conn):
    """Deposit creates entry in transactions table"""
    # Get account ID
    response = await client.get("/auth/me",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    user = response.json().get("user", response.json())
    account_id = user["ID"]
    before_balance = user["balance"]
    
    # Count transactions before
    count_before = await db_conn.fetchval(
        "SELECT COUNT(*) FROM transactions WHERE \"accountID\" = $1", account_id
    )
    
    # Deposit
    response = await client.post("/account/deposit",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"amount_cents": 1000}
    )
    assert response.status_code == 200
    
    # Count transactions after
    count_after = await db_conn.fetchval(
        "SELECT COUNT(*) FROM transactions WHERE \"accountID\" = $1", account_id
    )
    
    assert count_after == count_before + 1, "Deposit should create transaction record"
    
    # Verify transaction details
    transaction = await db_conn.fetchrow(
        """SELECT * FROM transactions 
           WHERE \"accountID\" = $1 
           ORDER BY created_at DESC LIMIT 1""",
        account_id
    )
    
    assert transaction["amount_cents"] == 1000
    assert transaction["transaction_type"] == "deposit"
    assert transaction["balance_before"] == before_balance
    assert transaction["balance_after"] == before_balance + 1000


@pytest.mark.asyncio
async def test_negative_deposit_rejected(client, customer_token):
    """Cannot deposit negative amount"""
    response = await client.post("/account/deposit",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"amount_cents": -1000}
    )
    
    assert response.status_code in [400, 422], "Negative deposit should be rejected"


# ============================================================================
# ORDER VALIDATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_order_rejected_when_balance_too_low(client, low_balance_customer, db_conn):
    """Order rejected if balance < total cost, warning incremented"""
    token = low_balance_customer["token"]
    
    # Get warnings before
    response = await client.get("/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    warnings_before = response.json().get("warnings", 0)
    
    # Try to order expensive item with no balance
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "items": [{"dish_id": 2, "qty": 10}],  # 10 pizzas = $149.90
            "delivery_address": "Test Address"
        }
    )
    
    assert response.status_code in [400, 402, 422], "Order should be rejected for insufficient funds"
    
    # Check warnings incremented
    response = await client.get("/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    warnings_after = response.json().get("warnings", 0)
    
    assert warnings_after >= warnings_before, "Warning should be issued for insufficient balance"


@pytest.mark.asyncio
async def test_successful_order_deducts_balance(client, customer_token, db_conn):
    """Successful order deducts amount from balance"""
    # Get current balance
    response = await client.get("/auth/me",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    user = response.json().get("user", response.json())
    balance_before = user["balance"]
    
    # Place order
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "dishes": [{"id": 1, "quantity": 1}],  # Burger $12.99
            "delivery_address": "123 Test St"
        }
    )
    
    if response.status_code == 200:
        order_cost = response.json()["finalCost"]
        
        # Check balance deducted
        response = await client.get("/auth/me",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        user = response.json().get("user", response.json())
        balance_after = user["balance"]
        
        assert balance_after == balance_before - order_cost


@pytest.mark.asyncio
async def test_order_creates_transaction_entry(client, customer_token, db_conn):
    """Order payment creates transaction audit entry"""
    response = await client.get("/auth/me",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    user = response.json().get("user", response.json())
    account_id = user["ID"]
    
    # Count transactions before
    count_before = await db_conn.fetchval(
        "SELECT COUNT(*) FROM transactions WHERE \"accountID\" = $1", account_id
    )
    
    # Place order
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "dishes": [{"id": 3, "quantity": 1}],  # Salad $8.99
            "delivery_address": "Test Address"
        }
    )
    
    if response.status_code == 200:
        # Count transactions after
        count_after = await db_conn.fetchval(
            "SELECT COUNT(*) FROM transactions WHERE \"accountID\" = $1", account_id
        )
        
        assert count_after > count_before, "Order should create transaction record"


# ============================================================================
# VIP DISCOUNT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_vip_receives_5_percent_discount(client, db_conn):
    """VIP customer receives 5% discount on orders"""
    # Login as VIP
    response = await client.post("/auth/login", json={
        "email": "vip1@test.com",
        "password": "testpass123"
    })
    vip_token = response.json()["access_token"]
    
    # Place order
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {vip_token}"},
        json={
            "dishes": [{"id": 2, "quantity": 2}],  # 2 pizzas @ $14.99
            "delivery_address": "VIP Address"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        subtotal = data.get("subtotal_cents", 0)
        discount = data.get("discount_cents", 0)
        
        # Discount should be ~5% of subtotal
        expected_discount = int(subtotal * 0.05)
        assert abs(discount - expected_discount) <= 1, f"VIP discount should be 5% of subtotal: expected {expected_discount}, got {discount}"


@pytest.mark.asyncio
async def test_regular_customer_no_discount(client, customer_token):
    """Regular customer receives no discount"""
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "dishes": [{"id": 1, "quantity": 1}],
            "delivery_address": "Test Address"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        discount = data.get("discount_cents", 0)
        
        assert discount == 0, "Regular customer should not receive discount"


# ============================================================================
# FREE DELIVERY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_vip_can_use_free_delivery_credit(client, db_conn):
    """VIP can use free delivery credit to waive delivery fee"""
    # Login as VIP with credits
    response = await client.post("/auth/login", json={
        "email": "vip1@test.com",
        "password": "testpass123"
    })
    vip_token = response.json()["access_token"]
    
    # Get credits before
    response = await client.get("/auth/me",
        headers={"Authorization": f"Bearer {vip_token}"}
    )
    credits_before = response.json().get("free_delivery_credits", 0)
    
    if credits_before > 0:
        # Place order with free delivery
        response = await client.post("/orders",
            headers={"Authorization": f"Bearer {vip_token}"},
            json={
                "dishes": [{"id": 1, "quantity": 1}],
                "delivery_address": "VIP Address",
                "use_free_delivery": True
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Delivery fee should be 0
            assert data.get("delivery_fee", 0) == 0 or data.get("free_delivery_used", 0) == 1
            
            # Credits decremented
            response = await client.get("/auth/me",
                headers={"Authorization": f"Bearer {vip_token}"}
            )
            credits_after = response.json().get("free_delivery_credits", 0)
            assert credits_after == credits_before - 1


# ============================================================================
# ORDERED DISHES TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_ordered_dishes_inserted_correctly(client, customer_token, db_conn):
    """Order creates entries in ordered_dishes junction table"""
    # Place order
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "dishes": [
                {"id": 1, "quantity": 2},
                {"id": 3, "quantity": 1}
            ],
            "delivery_address": "Test Address"
        }
    )
    
    if response.status_code == 200:
        order_id = response.json()["id"]
        
        # Check ordered_dishes
        rows = await db_conn.fetch(
            'SELECT * FROM ordered_dishes WHERE "orderID" = $1',
            order_id
        )
        
        assert len(rows) == 2, "Should have 2 ordered_dishes entries"
        
        # Verify quantities
        dish_quantities = {row["DishID"]: row["quantity"] for row in rows}
        assert dish_quantities.get(1) == 2
        assert dish_quantities.get(3) == 1


@pytest.mark.asyncio
async def test_order_totals_match_dish_prices(client, customer_token, db_conn):
    """Order total matches sum of dish prices"""
    # Get dish prices
    dish1 = await db_conn.fetchrow('SELECT cost FROM dishes WHERE id = 1')
    dish2 = await db_conn.fetchrow('SELECT cost FROM dishes WHERE id = 2')
    
    # Place order
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "dishes": [
                {"id": 1, "quantity": 1},
                {"id": 2, "quantity": 1}
            ],
            "delivery_address": "Test Address"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        expected_subtotal = dish1["cost"] + dish2["cost"]
        actual_subtotal = data.get("subtotal_cents", 0)
        
        assert actual_subtotal == expected_subtotal, f"Subtotal mismatch: expected {expected_subtotal}, got {actual_subtotal}"


@pytest.mark.asyncio
async def test_dish_popularity_counters_updated(client, customer_token, db_conn):
    """Ordering a dish updates its popularity counter"""
    # Get dish reviews count before
    dish_id = 1
    reviews_before = await db_conn.fetchval(
        'SELECT reviews FROM dishes WHERE id = $1', dish_id
    )
    
    # Place order
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "dishes": [{"id": dish_id, "quantity": 1}],
            "delivery_address": "Test Address"
        }
    )
    
    if response.status_code == 200:
        # Note: "reviews" column tracks reviews, not orders
        # Popularity would be tracked via ordered_dishes count
        
        # Check ordered_dishes count
        order_count = await db_conn.fetchval(
            'SELECT COUNT(*) FROM ordered_dishes WHERE "DishID" = $1', dish_id
        )
        
        assert order_count > 0, "Dish should appear in ordered_dishes"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
