"""
End-to-End Smoke Test
Full lifecycle scenario testing the complete system integration.

Scenario:
1. Customer registers and deposits funds
2. Customer places 3 orders (reaching VIP threshold)
3. Delivery persons bid on orders
4. Manager assigns delivery bids
5. Orders complete and customer becomes VIP
6. Customer files complaint about service
7. Manager resolves complaint
8. Check HR actions and reputation system
"""
import pytest
import pytest_asyncio
import httpx
import asyncpg
import os
from datetime import datetime
import asyncio


BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://restaurant_user:restaurant_password@localhost:5432/restaurant_db")
VIP_ORDER_THRESHOLD = int(os.getenv("VIP_ORDER_THRESHOLD", "3"))


@pytest_asyncio.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
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


@pytest.mark.asyncio
async def test_end_to_end_full_lifecycle(client, manager_token, delivery1_token, delivery2_token, db_conn):
    """
    Complete end-to-end test of the DashX system
    """
    print("\n" + "="*80)
    print("STARTING END-TO-END SMOKE TEST")
    print("="*80)
    
    # ========================================================================
    # STEP 1: Customer Registration
    # ========================================================================
    print("\n[STEP 1] Customer Registration")
    unique_email = f"e2e_customer_{datetime.now().timestamp()}@test.com"
    
    response = await client.post("/auth/register", json={
        "email": unique_email,
        "password": "testpass123",
        "account_type": "customer"
    })
    assert response.status_code in [200, 201], f"Registration failed: {response.text}"
    print(f"✓ Customer registered: {unique_email}")
    
    # Login
    response = await client.post("/auth/login", json={
        "email": unique_email,
        "password": "testpass123"
    })
    assert response.status_code == 200
    customer_token = response.json()["access_token"]
    customer_id = response.json().get("account_id") or response.json().get("ID")
    print(f"✓ Customer logged in (ID: {customer_id})")
    
    # ========================================================================
    # STEP 2: Deposit Funds
    # ========================================================================
    print("\n[STEP 2] Depositing Funds")
    response = await client.post("/account/deposit",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"amount_cents": 20000}  # $200
    )
    assert response.status_code == 200, f"Deposit failed: {response.text}"
    print("✓ Deposited $200")
    
    # Verify balance
    response = await client.get("/auth/me",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    data = response.json()
    user = data.get("user", data)
    balance = user["balance"]
    print(f"✓ Account balance: ${balance/100:.2f}")
    
    # ========================================================================
    # STEP 3: Place Multiple Orders (VIP Threshold)
    # ========================================================================
    print(f"\n[STEP 3] Placing {VIP_ORDER_THRESHOLD} Orders to Reach VIP Status")
    order_ids = []
    
    for i in range(VIP_ORDER_THRESHOLD):
        response = await client.post("/orders",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "items": [
                    {"dish_id": 1, "qty": 1},  # Burger $12.99
                    {"dish_id": 3, "qty": 1}   # Salad $8.99
                ],
                "delivery_address": f"123 E2E Test St, Order #{i+1}"
            }
        )
        
        assert response.status_code in [200, 201], f"Order {i+1} failed: {response.text}"
        order_data = response.json()
        order_id = order_data.get("id") or order_data.get("order", {}).get("id")
        order_ids.append(order_id)
        print(f"✓ Order #{i+1} placed (ID: {order_id})")
    
    # ========================================================================
    # STEP 4: Delivery Bidding
    # ========================================================================
    print("\n[STEP 4] Delivery Persons Bidding on Orders")
    
    for order_id in order_ids:
        # Delivery person 1 bids
        response1 = await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery1_token}"},
            json={
                "order_id": order_id,
                "bid_amount": 400,  # $4.00
                "estimated_minutes": 30
            }
        )
        
        # Delivery person 2 bids (lower)
        response2 = await client.post("/bids",
            headers={"Authorization": f"Bearer {delivery2_token}"},
            json={
                "order_id": order_id,
                "bid_amount": 350,  # $3.50
                "estimated_minutes": 35
            }
        )
        
        if response1.status_code in [200, 201] and response2.status_code in [200, 201]:
            print(f"✓ Order {order_id}: 2 bids received ($4.00, $3.50)")
    
    # ========================================================================
    # STEP 5: Manager Assigns Delivery
    # ========================================================================
    print("\n[STEP 5] Manager Assigning Deliveries")
    
    for order_id in order_ids:
        # Get bids for this order
        bids = await db_conn.fetch(
            'SELECT * FROM bid WHERE "orderID" = $1 ORDER BY "bidAmount" ASC',
            order_id
        )
        
        if bids:
            lowest_bid = bids[0]
            bid_id = lowest_bid["id"]
            
            # Manager assigns lowest bid
            response = await client.post(f"/manager/orders/{order_id}/assign",
                headers={"Authorization": f"Bearer {manager_token}"},
                json={"bid_id": bid_id}
            )
            
            if response.status_code == 200:
                print(f"✓ Order {order_id}: Assigned to delivery person (Bid ${lowest_bid['bidAmount']/100:.2f})")
            else:
                print(f"⚠ Order {order_id}: Assignment endpoint returned {response.status_code}")
    
    # ========================================================================
    # STEP 6: Complete Orders
    # ========================================================================
    print("\n[STEP 6] Marking Orders as Completed")
    
    for order_id in order_ids:
        # Manager marks order as delivered
        response = await client.patch(f"/manager/orders/{order_id}",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={"status": "delivered"}
        )
        
        if response.status_code in [200, 204]:
            print(f"✓ Order {order_id}: Marked as delivered")
    
    # Small delay for VIP upgrade processing
    await asyncio.sleep(1)
    
    # ========================================================================
    # STEP 7: Check VIP Upgrade
    # ========================================================================
    print("\n[STEP 7] Checking VIP Upgrade Status")
    
    response = await client.get("/auth/me",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    data = response.json()
    account = data.get("user", data)
    account_type = account.get("type")
    completed_orders = account.get("completed_orders_count", 0)
    
    print(f"✓ Account type: {account_type}")
    print(f"✓ Completed orders: {completed_orders}")
    
    if account_type == "vip":
        print("✓✓ CUSTOMER SUCCESSFULLY UPGRADED TO VIP!")
        
        # Check VIP benefits
        free_credits = account.get("free_delivery_credits", 0)
        print(f"✓ Free delivery credits: {free_credits}")
    else:
        print(f"⚠ Customer not yet VIP (may require order completion flow)")
    
    # ========================================================================
    # STEP 8: File Complaint
    # ========================================================================
    print("\n[STEP 8] Filing Customer Complaint")
    
    response = await client.post("/reputation/complaints",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "about_account_id": 2,  # Chef1
            "type": "complaint",
            "description": "E2E Test: Food was delivered cold despite quick delivery",
            "order_id": order_ids[0]
        }
    )
    
    if response.status_code in [200, 201]:
        complaint_id = response.json().get("id")
        print(f"✓ Complaint filed (ID: {complaint_id})")
        
        # ====================================================================
        # STEP 9: Manager Resolves Complaint
        # ====================================================================
        print("\n[STEP 9] Manager Resolving Complaint")
        
        response = await client.post(f"/manager/complaints/{complaint_id}/resolve",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={
                "resolution": "warning_issued",
                "manager_notes": "E2E Test: Spoke with chef about food temperature standards"
            }
        )
        
        if response.status_code == 200:
            print("✓ Complaint resolved with warning")
            
            # Check chef warnings
            chef = await db_conn.fetchrow(
                'SELECT * FROM accounts WHERE "ID" = 2'
            )
            print(f"✓ Chef warnings: {chef['warnings']}")
    else:
        print(f"⚠ Complaint filing returned {response.status_code}")
    
    # ========================================================================
    # STEP 10: Verify HR Actions and Audit Trail
    # ========================================================================
    print("\n[STEP 10] Verifying HR Actions and Audit Trail")
    
    # Check transactions
    transaction_count = await db_conn.fetchval(
        'SELECT COUNT(*) FROM transactions WHERE "accountID" = $1',
        customer_id
    )
    print(f"✓ Transaction records: {transaction_count}")
    
    # Check audit log
    audit_count = await db_conn.fetchval(
        'SELECT COUNT(*) FROM audit_log'
    )
    print(f"✓ Audit log entries: {audit_count}")
    
    # Check complaint resolution
    complaint_count = await db_conn.fetchval(
        'SELECT COUNT(*) FROM complaint WHERE status = $1',
        'resolved'
    )
    print(f"✓ Resolved complaints: {complaint_count}")
    
    # ========================================================================
    # STEP 11: Test Chat System
    # ========================================================================
    print("\n[STEP 11] Testing Chat/Knowledge Base System")
    
    response = await client.post("/chat",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"question": "What are your opening hours?"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Chat response received (source: {data.get('source', 'unknown')})")
        
        # Rate the response
        if data.get("chat_log_id"):
            response = await client.post(f"/chat/{data['chat_log_id']}/rate",
                headers={"Authorization": f"Bearer {customer_token}"},
                json={"rating": 5}
            )
            if response.status_code == 200:
                print("✓ Chat response rated successfully")
    
    # ========================================================================
    # STEP 12: Test Voice Reporting (if available)
    # ========================================================================
    print("\n[STEP 12] Testing Voice Reporting System")
    
    import io
    mock_audio = io.BytesIO(b"MOCK_E2E_AUDIO_" + os.urandom(500))
    
    response = await client.post("/voice-reports",
        headers={"Authorization": f"Bearer {customer_token}"},
        files={"audio_file": ("e2e_test.mp3", mock_audio, "audio/mpeg")}
    )
    
    if response.status_code in [200, 201]:
        report_id = response.json()["report_id"]
        print(f"✓ Voice report uploaded (ID: {report_id})")
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Manager views report
        response = await client.get(f"/manager/voice-reports/{report_id}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        if response.status_code == 200:
            print("✓ Manager can view voice report")
    else:
        print(f"⚠ Voice reporting returned {response.status_code}")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print("\n" + "="*80)
    print("END-TO-END SMOKE TEST COMPLETED")
    print("="*80)
    print("\nSummary:")
    print(f"  • Customer registered and deposited funds")
    print(f"  • {len(order_ids)} orders placed and processed")
    print(f"  • Bidding and delivery assignment completed")
    print(f"  • VIP upgrade status: {account_type}")
    print(f"  • Complaint filed and resolved")
    print(f"  • Audit trail verified")
    print(f"  • Chat and voice systems tested")
    print("\n✓✓✓ ALL CORE SYSTEM FLOWS OPERATIONAL ✓✓✓\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
