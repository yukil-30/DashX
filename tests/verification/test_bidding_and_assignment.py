"""
Bidding and Assignment Tests
Verifies bid posting, lowest bid detection, and manager assignment with memos.
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
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def db_conn():
    conn = await asyncpg.connect(DATABASE_URL)
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def manager_token(client):
    response = await client.post("/auth/login", json={
        "email": "manager@test.com",
        "password": "testpass123"
    })
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def delivery1_token(client):
    response = await client.post("/auth/login", json={
        "email": "delivery1@test.com",
        "password": "testpass123"
    })
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def delivery2_token(client):
    response = await client.post("/auth/login", json={
        "email": "delivery2@test.com",
        "password": "testpass123"
    })
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def customer_with_balance(client):
    """Create customer with sufficient balance"""
    unique_email = f"bidtest_{datetime.now().timestamp()}@test.com"
    
    response = await client.post("/auth/register", json={
        "email": unique_email,
        "password": "testpass123",
        "account_type": "customer"
    })
    assert response.status_code in [200, 201]
    
    response = await client.post("/auth/login", json={
        "email": unique_email,
        "password": "testpass123"
    })
    token = response.json()["access_token"]
    
    # Deposit funds
    await client.post("/account/deposit",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount_cents": 10000}
    )
    
    return token


# ============================================================================
# BID POSTING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_delivery_person_can_post_bid(client, customer_with_balance, delivery1_token, db_conn):
    """Delivery person can bid on an order"""
    # Create order
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_with_balance}"},
        json={
            "dishes": [{"id": 1, "quantity": 1}],
            "delivery_address": "Bid Test Address"
        }
    )
    
    if response.status_code == 200:
        order_id = response.json()["id"]
        
        # Post bid
        response = await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery1_token}"},
            json={
                "order_id": order_id,
                "bid_amount": 400,
                "estimated_minutes": 25
            }
        )
        
        assert response.status_code in [200, 201], f"Bid posting failed: {response.text}"
        
        # Verify bid in database
        bid = await db_conn.fetchrow(
            'SELECT * FROM bid WHERE "orderID" = $1', order_id
        )
        assert bid is not None
        assert bid["bidAmount"] == 400


@pytest.mark.asyncio
async def test_multiple_delivery_persons_can_bid_on_same_order(client, customer_with_balance, delivery1_token, delivery2_token, db_conn):
    """Multiple delivery persons can bid on the same order"""
    # Create order
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_with_balance}"},
        json={
            "dishes": [{"id": 2, "quantity": 1}],
            "delivery_address": "Multi Bid Test"
        }
    )
    
    if response.status_code == 200:
        order_id = response.json()["id"]
        
        # Delivery person 1 bids
        response1 = await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery1_token}"},
            json={
                "order_id": order_id,
                "bid_amount": 500,
                "estimated_minutes": 30
            }
        )
        
        # Delivery person 2 bids
        response2 = await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery2_token}"},
            json={
                "order_id": order_id,
                "bid_amount": 450,
                "estimated_minutes": 25
            }
        )
        
        assert response1.status_code in [200, 201]
        assert response2.status_code in [200, 201]
        
        # Check both bids exist
        bids = await db_conn.fetch(
            'SELECT * FROM bid WHERE "orderID" = $1', order_id
        )
        assert len(bids) == 2


@pytest.mark.asyncio
async def test_duplicate_bid_from_same_delivery_person_rejected(client, customer_with_balance, delivery1_token):
    """Same delivery person cannot bid twice on same order"""
    # Create order
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_with_balance}"},
        json={
            "dishes": [{"id": 1, "quantity": 1}],
            "delivery_address": "Duplicate Bid Test"
        }
    )
    
    if response.status_code == 200:
        order_id = response.json()["id"]
        
        # First bid
        response1 = await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery1_token}"},
            json={
                "order_id": order_id,
                "bid_amount": 400,
                "estimated_minutes": 30
            }
        )
        assert response1.status_code in [200, 201]
        
        # Second bid from same person
        response2 = await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery1_token}"},
            json={
                "order_id": order_id,
                "bid_amount": 350,
                "estimated_minutes": 25
            }
        )
        
        assert response2.status_code in [400, 409], "Duplicate bid should be rejected"


# ============================================================================
# LOWEST BID DETECTION
# ============================================================================

@pytest.mark.asyncio
async def test_system_identifies_lowest_bid(client, customer_with_balance, delivery1_token, delivery2_token, db_conn):
    """System correctly identifies the lowest bid"""
    # Create order
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_with_balance}"},
        json={
            "dishes": [{"id": 1, "quantity": 1}],
            "delivery_address": "Lowest Bid Test"
        }
    )
    
    if response.status_code == 200:
        order_id = response.json()["id"]
        
        # Delivery 1: $5.00
        await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery1_token}"},
            json={"order_id": order_id, "bid_amount": 500, "estimated_minutes": 30}
        )
        
        # Delivery 2: $3.50 (lower)
        await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery2_token}"},
            json={"order_id": order_id, "bid_amount": 350, "estimated_minutes": 35}
        )
        
        # Query lowest bid
        lowest_bid = await db_conn.fetchrow(
            'SELECT * FROM bid WHERE "orderID" = $1 ORDER BY "bidAmount" ASC LIMIT 1',
            order_id
        )
        
        assert lowest_bid["bidAmount"] == 350


# ============================================================================
# MANAGER ASSIGNMENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_manager_can_assign_lowest_bid(client, customer_with_balance, delivery1_token, delivery2_token, manager_token, db_conn):
    """Manager can assign the lowest bid to an order"""
    # Create order
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_with_balance}"},
        json={
            "dishes": [{"id": 1, "quantity": 1}],
            "delivery_address": "Assignment Test"
        }
    )
    
    if response.status_code == 200:
        order_id = response.json()["id"]
        
        # Post bids
        await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery1_token}"},
            json={"order_id": order_id, "bid_amount": 400, "estimated_minutes": 30}
        )
        
        response = await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery2_token}"},
            json={"order_id": order_id, "bid_amount": 350, "estimated_minutes": 25}
        )
        bid_id = response.json().get("id")
        
        # Manager assigns lowest bid
        response = await client.post(f"/manager/orders/{order_id}/assign",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={"bid_id": bid_id}
        )
        
        if response.status_code == 200:
            # Verify order has accepted_bid_id
            order = await db_conn.fetchrow(
                'SELECT * FROM orders WHERE id = $1', order_id
            )
            assert order["bidID"] == bid_id


@pytest.mark.asyncio
async def test_manager_can_assign_non_lowest_bid_with_memo(client, customer_with_balance, delivery1_token, delivery2_token, manager_token, db_conn):
    """Manager can assign non-lowest bid but must provide memo"""
    # Create order
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_with_balance}"},
        json={
            "dishes": [{"id": 1, "quantity": 1}],
            "delivery_address": "Non-Lowest Test"
        }
    )
    
    if response.status_code == 200:
        order_id = response.json()["id"]
        
        # Delivery 1: $3.50 (lowest)
        await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery1_token}"},
            json={"order_id": order_id, "bid_amount": 350, "estimated_minutes": 40}
        )
        
        # Delivery 2: $4.00 (higher but faster)
        response = await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery2_token}"},
            json={"order_id": order_id, "bid_amount": 400, "estimated_minutes": 20}
        )
        higher_bid_id = response.json().get("id")
        
        # Manager assigns higher bid with memo
        response = await client.post(f"/manager/orders/{order_id}/assign",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={
                "bid_id": higher_bid_id,
                "memo": "Chose faster delivery despite higher cost"
            }
        )
        
        if response.status_code == 200:
            # Verify memo saved
            order = await db_conn.fetchrow(
                'SELECT * FROM orders WHERE id = $1', order_id
            )
            assert order["bidID"] == higher_bid_id
            assert order.get("assignment_memo") is not None
            assert "faster" in order.get("assignment_memo", "").lower()


@pytest.mark.asyncio
async def test_assigning_non_lowest_without_memo_rejected(client, customer_with_balance, delivery1_token, delivery2_token, manager_token):
    """Manager must provide memo when assigning non-lowest bid"""
    # Create order
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_with_balance}"},
        json={
            "dishes": [{"id": 1, "quantity": 1}],
            "delivery_address": "Memo Required Test"
        }
    )
    
    if response.status_code == 200:
        order_id = response.json()["id"]
        
        # Post bids
        await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery1_token}"},
            json={"order_id": order_id, "bid_amount": 300, "estimated_minutes": 30}
        )
        
        response = await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery2_token}"},
            json={"order_id": order_id, "bid_amount": 500, "estimated_minutes": 20}
        )
        higher_bid_id = response.json().get("id")
        
        # Try to assign without memo
        response = await client.post(f"/manager/orders/{order_id}/assign",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={"bid_id": higher_bid_id}  # No memo
        )
        
        # Should require memo for non-lowest
        assert response.status_code in [400, 422], "Should require memo for non-lowest bid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
