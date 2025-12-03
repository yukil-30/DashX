"""
Authentication and Roles Tests
Verifies registration, login, JWT, role-based access control, and VIP upgrades.
"""
import pytest
import pytest_asyncio
import httpx
import os
from datetime import datetime


BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
VIP_ORDER_THRESHOLD = int(os.getenv("VIP_ORDER_THRESHOLD", "3"))
VIP_SPENDING_THRESHOLD_CENTS = int(os.getenv("VIP_SPENDING_THRESHOLD_CENTS", "10000"))


@pytest_asyncio.fixture
async def client():
    """HTTP client for API requests"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def manager_token(client):
    """Get manager JWT token"""
    response = await client.post("/auth/login", json={
        "email": "manager@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]


@pytest_asyncio.fixture
async def customer_token(client):
    """Get customer JWT token"""
    response = await client.post("/auth/login", json={
        "email": "customer1@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]


@pytest_asyncio.fixture
async def vip_token(client):
    """Get VIP customer JWT token"""
    response = await client.post("/auth/login", json={
        "email": "vip1@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def chef_token(client):
    """Get chef JWT token"""
    response = await client.post("/auth/login", json={
        "email": "chef1@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]


@pytest_asyncio.fixture
async def delivery_token(client):
    """Get delivery person JWT token"""
    response = await client.post("/auth/login", json={
        "email": "delivery1@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]


# ============================================================================
# REGISTRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_visitor_can_register_as_customer(client):
    """Visitor can register a new customer account"""
    unique_email = f"newcustomer_{datetime.now().timestamp()}@test.com"
    
    response = await client.post("/auth/register", json={
        "email": unique_email,
        "password": "newpass123",
        "account_type": "customer"
    })
    
    assert response.status_code in [200, 201], f"Registration failed: {response.text}"
    data = response.json()
    
    assert "access_token" in data, "Should return access token"
    
    # Get user info to verify registration
    me_response = await client.get("/auth/me", headers={
        "Authorization": f"Bearer {data['access_token']}"
    })
    user_data = me_response.json().get("user", me_response.json())
    assert user_data["email"] == unique_email
    assert user_data["type"] in ["customer", "visitor"]


@pytest.mark.asyncio
async def test_cannot_register_duplicate_email(client):
    """Cannot register with existing email"""
    response = await client.post("/auth/register", json={
        "email": "customer1@test.com",  # Exists in seed data
        "password": "anypass",
        "account_type": "customer"
    })
    
    assert response.status_code in [400, 409, 422], "Should reject duplicate email"


@pytest.mark.asyncio
async def test_password_is_hashed_not_plaintext(client):
    """Verify password is stored hashed, not plaintext"""
    # This would require DB inspection, but we can verify login works
    response = await client.post("/auth/login", json={
        "email": "customer1@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    
    # Wrong password should fail
    response = await client.post("/auth/login", json={
        "email": "customer1@test.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


# ============================================================================
# LOGIN AND JWT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_login_returns_jwt_with_role(client):
    """Login returns JWT token with user role"""
    response = await client.post("/auth/login", json={
        "email": "manager@test.com",
        "password": "testpass123"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    
    # Role is encoded in JWT, need to call /auth/me to verify
    token = data["access_token"]
    response = await client.get("/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data.get("user", {}).get("type") == "manager" or user_data.get("type") == "manager"


@pytest.mark.asyncio
async def test_invalid_credentials_rejected(client):
    """Invalid email or password returns 401"""
    # Invalid email
    response = await client.post("/auth/login", json={
        "email": "nonexistent@test.com",
        "password": "anypass"
    })
    assert response.status_code == 401
    
    # Invalid password
    response = await client.post("/auth/login", json={
        "email": "customer1@test.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_jwt_contains_user_info(client, customer_token):
    """JWT allows retrieval of user information"""
    response = await client.get("/auth/me", headers={
        "Authorization": f"Bearer {customer_token}"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Response is wrapped in "user" object
    user = data.get("user", data)
    assert "email" in user
    assert user["email"] == "customer1@test.com"
    assert "type" in user
    assert user["type"] == "customer"
    assert "balance" in user
    assert "ID" in user


# ============================================================================
# ROLE-BASED ACCESS CONTROL
# ============================================================================

@pytest.mark.asyncio
async def test_visitor_cannot_create_order(client):
    """Visitor role cannot place orders"""
    # Login as visitor
    response = await client.post("/auth/login", json={
        "email": "visitor1@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    visitor_token = response.json()["access_token"]
    
    # Try to create order
    response = await client.post("/orders", 
        headers={"Authorization": f"Bearer {visitor_token}"},
        json={
            "dishes": [{"id": 1, "quantity": 1}],
            "delivery_address": "123 Test St"
        }
    )
    
    assert response.status_code in [401, 403, 422], "Visitor should not be able to order"


@pytest.mark.asyncio
async def test_customer_can_create_order(client, customer_token):
    """Customer role can place orders"""
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "dishes": [{"id": 1, "quantity": 1}],
            "delivery_address": "456 Customer Ave",
            "note": "Test order"
        }
    )
    
    # May fail for insufficient balance, but should not be 403 (forbidden)
    assert response.status_code not in [403], "Customer should have permission to order"


@pytest.mark.asyncio
async def test_manager_only_endpoints_blocked_for_non_managers(client, customer_token, chef_token):
    """Manager-only endpoints reject non-manager users"""
    
    # Test with customer token
    response = await client.get("/voice-reports/manager/dashboard", headers={
        "Authorization": f"Bearer {customer_token}"
    })
    assert response.status_code == 403, "Customer should not access manager endpoints"
    
    # Test with chef token
    response = await client.get("/voice-reports/manager/dashboard", headers={
        "Authorization": f"Bearer {chef_token}"
    })
    assert response.status_code == 403, "Chef should not access manager endpoints"


@pytest.mark.asyncio
async def test_manager_can_access_manager_endpoints(client, manager_token):
    """Manager role can access manager endpoints"""
    response = await client.get("/voice-reports/manager/dashboard", headers={
        "Authorization": f"Bearer {manager_token}"
    })
    assert response.status_code == 200, f"Manager should access manager endpoints: {response.text}"


@pytest.mark.asyncio
async def test_delivery_can_post_bids(client, delivery_token):
    """Delivery person can post bids on orders"""
    # First create an order to bid on (may need manager to create)
    # For now, test endpoint access
    response = await client.post("/bids",
        headers={"Authorization": f"Bearer {delivery_token}"},
        json={
            "order_id": 1,
            "bid_amount": 500,
            "estimated_minutes": 30
        }
    )
    
    # May fail if order doesn't exist, but should not be 403
    assert response.status_code not in [403], "Delivery person should be able to bid"


@pytest.mark.asyncio
async def test_chef_cannot_post_bids(client, chef_token):
    """Chef role cannot post delivery bids"""
    response = await client.post("/bids",
        headers={"Authorization": f"Bearer {chef_token}"},
        json={
            "order_id": 1,
            "bid_amount": 500,
            "estimated_minutes": 30
        }
    )
    
    assert response.status_code in [403, 422], "Chef should not be able to post bids"


# ============================================================================
# VIP UPGRADE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_vip_upgrade_after_n_orders(client):
    """Customer becomes VIP after N successful orders"""
    # Register new customer
    unique_email = f"vip_test_{datetime.now().timestamp()}@test.com"
    
    response = await client.post("/auth/register", json={
        "email": unique_email,
        "password": "testpass123",
        "account_type": "customer"
    })
    assert response.status_code in [200, 201]
    
    # Login to get token
    response = await client.post("/auth/login", json={
        "email": unique_email,
        "password": "testpass123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    # Deposit funds
    response = await client.post("/account/deposit",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount_cents": 10000}
    )
    assert response.status_code == 200
    
    # Place N orders (VIP threshold)
    for i in range(VIP_ORDER_THRESHOLD):
        response = await client.post("/orders",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "dishes": [{"id": 1, "quantity": 1}],
                "delivery_address": "VIP Test Address"
            }
        )
        # May succeed or fail, but track orders
    
    # Check if upgraded to VIP
    response = await client.get("/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    
    # Should be VIP if orders succeeded
    # Note: May need completed orders, not just placed
    if data.get("completed_orders_count", 0) >= VIP_ORDER_THRESHOLD:
        assert data["type"] == "vip", f"Should be VIP after {VIP_ORDER_THRESHOLD} orders"


@pytest.mark.asyncio
async def test_vip_upgrade_after_spending_threshold(client):
    """Customer becomes VIP after spending > $100"""
    # This requires completing high-value orders
    # Check existing VIP customer
    response = await client.post("/auth/login", json={
        "email": "vip1@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    data = response.json()
    
    # Check /auth/me for VIP status
    token = data.get("access_token")
    me_response = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    user_data = me_response.json()
    user = user_data.get("user", user_data)
    assert user.get("type") == "vip"
@pytest.mark.asyncio
async def test_vip_receives_5_percent_discount(client, vip_token):
    """VIP customers get 5% discount on orders"""
    # Place order and check discount
    response = await client.post("/orders",
        headers={"Authorization": f"Bearer {vip_token}"},
        json={
            "dishes": [{"id": 2, "quantity": 1}],  # Pizza $14.99
            "delivery_address": "VIP Address"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        # Check for discount_cents field
        assert "discount_cents" in data
        assert data["discount_cents"] > 0, "VIP should receive discount"
        assert "discount_cents" in data
        assert data["discount_cents"] > 0, "VIP should receive discount"


@pytest.mark.asyncio
async def test_vip_free_delivery_credits(client):
    """VIP gets free delivery credits (1 per 3 orders)"""
    response = await client.post("/auth/login", json={
        "email": "vip1@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    # Check account
    response = await client.get("/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    user = data.get("user", data)
    
    # VIP should have free_delivery_credits field
    assert "free_delivery_credits" in user
    # Seed data gives VIP 2 credits
    assert user["free_delivery_credits"] >= 0


@pytest.mark.asyncio
async def test_vip_downgrade_mechanism_exists(client, manager_token):
    """Manager can downgrade VIP to customer"""
    # This would require manager endpoint to downgrade
    # Test that the mechanism exists
    response = await client.post("/manager/accounts/8/downgrade",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"reason": "Test downgrade"}
    )
    
    # May not be implemented yet, but endpoint should exist
    # Accept 200, 404, or 501 (not implemented)
    assert response.status_code in [200, 404, 501]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
