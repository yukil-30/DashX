"""
Tests for order endpoints
Covers:
- Order creation with deposit deduction
- Insufficient deposit rejection with warning increment
- VIP discount application (5%)
- VIP free delivery credits (every 3 orders)
- Delivery bidding
- Manager assignment
- Transaction audit logging
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timezone

from app.main import app
from app.auth import create_access_token, get_current_user, require_manager
from app.database import get_db
from app.models import Account, Dish, Order, OrderedDish, Bid, Transaction


client = TestClient(app)


# ============================================================
# Mock Factories
# ============================================================

def create_mock_user(
    ID=1,
    email="customer@example.com",
    balance=10000,  # $100.00
    user_type="customer",
    warnings=0,
    free_delivery_credits=0,
    completed_orders_count=0
):
    """Create a mock user for testing"""
    mock_user = MagicMock(spec=Account)
    mock_user.ID = ID
    mock_user.email = email
    mock_user.type = user_type
    mock_user.balance = balance
    mock_user.warnings = warnings
    mock_user.free_delivery_credits = free_delivery_credits
    mock_user.completed_orders_count = completed_orders_count
    mock_user.wage = None
    mock_user.restaurantID = 1
    return mock_user


def create_mock_dish(id=1, name="Test Dish", cost=1000, restaurantID=1):
    """Create a mock dish"""
    mock_dish = MagicMock(spec=Dish)
    mock_dish.id = id
    mock_dish.name = name
    mock_dish.cost = cost
    mock_dish.restaurantID = restaurantID
    mock_dish.description = "Test description"
    mock_dish.picture = None
    mock_dish.average_rating = 4.5
    mock_dish.reviews = 10
    mock_dish.chefID = None
    return mock_dish


def create_mock_order(
    id=1,
    accountID=1,
    finalCost=1500,
    status="paid",
    bidID=None,
    delivery_fee=500,
    subtotal_cents=1000,
    discount_cents=0,
    free_delivery_used=0
):
    """Create a mock order"""
    mock_order = MagicMock(spec=Order)
    mock_order.id = id
    mock_order.accountID = accountID
    mock_order.dateTime = datetime.now(timezone.utc).isoformat()
    mock_order.finalCost = finalCost
    mock_order.status = status
    mock_order.bidID = bidID
    mock_order.note = None
    mock_order.delivery_address = "123 Test St"
    mock_order.delivery_fee = delivery_fee
    mock_order.subtotal_cents = subtotal_cents
    mock_order.discount_cents = discount_cents
    mock_order.free_delivery_used = free_delivery_used
    mock_order.ordered_dishes = []
    return mock_order


def create_mock_bid(id=1, deliveryPersonID=2, orderID=1, bidAmount=300):
    """Create a mock bid"""
    mock_bid = MagicMock(spec=Bid)
    mock_bid.id = id
    mock_bid.deliveryPersonID = deliveryPersonID
    mock_bid.orderID = orderID
    mock_bid.bidAmount = bidAmount
    mock_bid.delivery_person = create_mock_user(
        ID=deliveryPersonID, 
        email="delivery@example.com", 
        user_type="delivery"
    )
    return mock_bid


def create_mock_db():
    """Create a mock database session"""
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.rollback = MagicMock()
    mock_db.flush = MagicMock()
    mock_db.refresh = MagicMock()
    return mock_db


# ============================================================
# Helper to get auth headers
# ============================================================

def get_auth_headers(email="customer@example.com", user_id=1):
    """Get authorization headers with a valid token"""
    token = create_access_token(data={"sub": email, "user_id": user_id})
    return {"Authorization": f"Bearer {token}"}


# ============================================================
# Order Creation Tests
# ============================================================

class TestOrderCreation:
    """Test POST /orders endpoint"""

    def test_create_order_success(self):
        """Test successful order creation with deposit deduction"""
        mock_user = create_mock_user(balance=10000)  # $100
        mock_db = create_mock_db()
        mock_dish = create_mock_dish(id=1, cost=1000)  # $10
        
        # Setup mock query to return dish
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_dish]
        
        # Track order and ordered dishes creation
        order_id_counter = [0]
        def capture_add(obj):
            if hasattr(obj, 'finalCost'):
                # It's an Order
                order_id_counter[0] += 1
                obj.id = order_id_counter[0]
                obj.ordered_dishes = []
            elif hasattr(obj, 'DishID'):
                # It's an OrderedDish - mock the relationship
                pass
        
        mock_db.add.side_effect = capture_add
        mock_db.flush.side_effect = lambda: None
        
        def mock_refresh(obj):
            if hasattr(obj, 'ordered_dishes'):
                # Mock ordered dishes with proper structure
                mock_od = MagicMock()
                mock_od.DishID = 1
                mock_od.quantity = 2
                obj.ordered_dishes = [mock_od]
        mock_db.refresh.side_effect = mock_refresh
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders", json={
                "items": [{"dish_id": 1, "qty": 2}],
                "delivery_address": "123 Test Street"
            })
            
            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
            data = response.json()
            assert data["message"] == "Order created successfully"
            # Subtotal: 2 * $10 = $20, Delivery: $5, Total: $25
            assert data["order"]["subtotal_cents"] == 2000
            assert data["order"]["delivery_fee"] == 500
            assert data["order"]["finalCost"] == 2500
            assert data["order"]["status"] == "paid"
            # Balance should be deducted
            assert data["new_balance"] == 10000 - 2500
        finally:
            app.dependency_overrides.clear()

    def test_create_order_insufficient_deposit(self):
        """Test order rejection when deposit is insufficient"""
        mock_user = create_mock_user(balance=500, warnings=0)  # Only $5
        mock_db = create_mock_db()
        mock_dish = create_mock_dish(id=1, cost=2000)  # $20 dish
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_dish]
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders", json={
                "items": [{"dish_id": 1, "qty": 1}],
                "delivery_address": "123 Test Street"
            })
            
            assert response.status_code == 402  # Payment Required
            data = response.json()
            assert data["detail"]["error"] == "insufficient_deposit"
            assert data["detail"]["warnings"] == 1  # Warning incremented
            assert data["detail"]["required_amount"] == 2500  # $20 dish + $5 delivery
            assert data["detail"]["current_balance"] == 500
            assert data["detail"]["shortfall"] == 2000
            
            # Verify warning was incremented on the user
            assert mock_user.warnings == 1
        finally:
            app.dependency_overrides.clear()

    def test_create_order_vip_discount(self):
        """Test VIP gets 5% discount on order"""
        mock_user = create_mock_user(
            balance=50000,  # $500
            user_type="vip",
            free_delivery_credits=0,
            completed_orders_count=0
        )
        mock_db = create_mock_db()
        mock_dish = create_mock_dish(id=1, cost=10000)  # $100 dish
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_dish]
        
        created_order = None
        def capture_add(obj):
            nonlocal created_order
            if hasattr(obj, 'finalCost'):
                created_order = obj
                obj.id = 1
        mock_db.add.side_effect = capture_add
        mock_db.flush.side_effect = lambda: setattr(created_order, 'id', 1) if created_order else None
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders", json={
                "items": [{"dish_id": 1, "qty": 1}],
                "delivery_address": "123 VIP Street"
            })
            
            assert response.status_code == 201
            data = response.json()
            # Subtotal: $100, 5% discount: $5, Delivery: $5, Total: $100
            assert data["order"]["subtotal_cents"] == 10000
            assert data["order"]["discount_cents"] == 500  # 5% of $100
            assert data["order"]["delivery_fee"] == 500
            assert data["order"]["finalCost"] == 10000  # $100 - $5 + $5
        finally:
            app.dependency_overrides.clear()

    def test_create_order_vip_free_delivery(self):
        """Test VIP with free delivery credits uses free delivery"""
        mock_user = create_mock_user(
            balance=50000,
            user_type="vip",
            free_delivery_credits=1,  # Has 1 free delivery
            completed_orders_count=3
        )
        mock_db = create_mock_db()
        mock_dish = create_mock_dish(id=1, cost=10000)
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_dish]
        
        created_order = None
        def capture_add(obj):
            nonlocal created_order
            if hasattr(obj, 'finalCost'):
                created_order = obj
                obj.id = 1
        mock_db.add.side_effect = capture_add
        mock_db.flush.side_effect = lambda: setattr(created_order, 'id', 1) if created_order else None
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders", json={
                "items": [{"dish_id": 1, "qty": 1}],
                "delivery_address": "123 VIP Street"
            })
            
            assert response.status_code == 201
            data = response.json()
            # Subtotal: $100, 5% discount: $5, Free Delivery: $0
            assert data["order"]["subtotal_cents"] == 10000
            assert data["order"]["discount_cents"] == 500
            assert data["order"]["delivery_fee"] == 0  # Free delivery used
            assert data["order"]["free_delivery_used"] == 1
            assert data["order"]["finalCost"] == 9500  # $100 - $5
            
            # Verify free delivery credit was consumed
            assert mock_user.free_delivery_credits == 0
        finally:
            app.dependency_overrides.clear()

    def test_create_order_vip_earns_free_delivery(self):
        """Test VIP earns free delivery credit after every 3 orders"""
        mock_user = create_mock_user(
            balance=50000,
            user_type="vip",
            free_delivery_credits=0,
            completed_orders_count=2  # Will become 3 after this order
        )
        mock_db = create_mock_db()
        mock_dish = create_mock_dish(id=1, cost=1000)
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_dish]
        
        created_order = None
        def capture_add(obj):
            nonlocal created_order
            if hasattr(obj, 'finalCost'):
                created_order = obj
                obj.id = 1
        mock_db.add.side_effect = capture_add
        mock_db.flush.side_effect = lambda: setattr(created_order, 'id', 1) if created_order else None
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders", json={
                "items": [{"dish_id": 1, "qty": 1}],
                "delivery_address": "123 VIP Street"
            })
            
            assert response.status_code == 201
            
            # After this order, completed_orders_count = 3
            # VIP should earn 1 free delivery credit
            assert mock_user.completed_orders_count == 3
            assert mock_user.free_delivery_credits == 1
        finally:
            app.dependency_overrides.clear()

    def test_create_order_dish_not_found(self):
        """Test order with non-existent dish"""
        mock_user = create_mock_user(balance=10000)
        mock_db = create_mock_db()
        
        # Return empty list (dish not found)
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders", json={
                "items": [{"dish_id": 999, "qty": 1}],
                "delivery_address": "123 Test Street"
            })
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_create_order_employee_forbidden(self):
        """Test that employees cannot place orders"""
        mock_user = create_mock_user(user_type="manager")
        mock_db = create_mock_db()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders", json={
                "items": [{"dish_id": 1, "qty": 1}],
                "delivery_address": "123 Test Street"
            })
            
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_create_order_no_items(self):
        """Test order with empty items list"""
        mock_user = create_mock_user(balance=10000)
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.post("/orders", json={
                "items": [],
                "delivery_address": "123 Test Street"
            })
            
            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Get Order Tests
# ============================================================

class TestGetOrder:
    """Test GET /orders/{id} endpoint"""

    def test_get_order_success(self):
        """Test getting order by owner"""
        mock_user = create_mock_user(ID=1)
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, accountID=1)
        
        # Setup mock ordered dishes
        mock_ordered_dish = MagicMock(spec=OrderedDish)
        mock_ordered_dish.DishID = 1
        mock_ordered_dish.quantity = 2
        mock_ordered_dish.dish = create_mock_dish(id=1)
        mock_order.ordered_dishes = [mock_ordered_dish]
        
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_order
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/orders/1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["accountID"] == 1
            assert data["status"] == "paid"
        finally:
            app.dependency_overrides.clear()

    def test_get_order_not_found(self):
        """Test getting non-existent order"""
        mock_user = create_mock_user()
        mock_db = create_mock_db()
        
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/orders/999")
            
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_get_order_forbidden(self):
        """Test that other customers cannot view someone else's order"""
        mock_user = create_mock_user(ID=2, user_type="customer")  # Different user
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, accountID=1)  # Order belongs to user 1
        
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_order
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/orders/1")
            
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_get_order_manager_allowed(self):
        """Test that managers can view any order"""
        mock_user = create_mock_user(ID=99, user_type="manager")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, accountID=1)
        mock_order.ordered_dishes = []
        
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_order
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/orders/1")
            
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Delivery Bidding Tests
# ============================================================

class TestDeliveryBidding:
    """Test POST /orders/{id}/bid endpoint"""

    def test_create_bid_success(self):
        """Test delivery person creating a bid"""
        mock_user = create_mock_user(ID=2, email="delivery@test.com", user_type="delivery")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_order,  # First call: get order
            None  # Second call: check existing bid (none)
        ]
        
        created_bid = None
        def capture_add(obj):
            nonlocal created_bid
            created_bid = obj
            obj.id = 1
        mock_db.add.side_effect = capture_add
        mock_db.refresh.side_effect = lambda obj: setattr(obj, 'id', 1)
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders/1/bid", json={
                "price_cents": 300
            })
            
            assert response.status_code == 201
            data = response.json()
            assert data["bidAmount"] == 300
            assert data["deliveryPersonID"] == 2
            assert data["orderID"] == 1
        finally:
            app.dependency_overrides.clear()

    def test_create_bid_non_delivery_forbidden(self):
        """Test that non-delivery personnel cannot bid"""
        mock_user = create_mock_user(user_type="customer")
        mock_db = create_mock_db()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders/1/bid", json={
                "price_cents": 300
            })
            
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_create_bid_order_not_open(self):
        """Test bidding on order that's not in 'paid' status"""
        mock_user = create_mock_user(ID=2, user_type="delivery")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="assigned")  # Already assigned
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_order
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders/1/bid", json={
                "price_cents": 300
            })
            
            assert response.status_code == 400
            assert "not open for bidding" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_create_bid_duplicate_rejected(self):
        """Test that same delivery person cannot bid twice on same order"""
        mock_user = create_mock_user(ID=2, user_type="delivery")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        existing_bid = create_mock_bid(id=1, deliveryPersonID=2, orderID=1)
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_order,  # First call: get order
            existing_bid  # Second call: existing bid found
        ]
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders/1/bid", json={
                "price_cents": 200
            })
            
            assert response.status_code == 400
            assert "already submitted a bid" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


# ============================================================
# List Bids Tests
# ============================================================

class TestListBids:
    """Test GET /orders/{id}/bids endpoint"""

    def test_list_bids_success(self):
        """Test listing all bids for an order"""
        mock_user = create_mock_user(ID=1)  # Order owner
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, accountID=1)
        mock_bid1 = create_mock_bid(id=1, deliveryPersonID=2, bidAmount=300)
        mock_bid2 = create_mock_bid(id=2, deliveryPersonID=3, bidAmount=250)
        
        # Mock delivery rating
        from decimal import Decimal
        mock_rating = MagicMock()
        mock_rating.accountID = 2
        mock_rating.averageRating = Decimal("4.5")
        mock_rating.reviews = 10
        mock_rating.total_deliveries = 50
        mock_rating.on_time_deliveries = 45
        mock_rating.avg_delivery_minutes = 25
        
        # Setup mock query chains
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        bids_query = MagicMock()
        bids_query.options.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_bid1, mock_bid2]
        
        rating_query = MagicMock()
        rating_query.filter.return_value.first.return_value = mock_rating
        
        def query_side_effect(model):
            from app.models import DeliveryRating
            if model == Order:
                return order_query
            elif model == Bid:
                return bids_query
            elif model == DeliveryRating:
                return rating_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/orders/1/bids")
            
            assert response.status_code == 200
            data = response.json()
            assert data["order_id"] == 1
            assert len(data["bids"]) == 2
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Assign Delivery Tests
# ============================================================

class TestAssignDelivery:
    """Test POST /orders/{id}/assign endpoint"""

    def test_assign_delivery_success(self):
        """Test manager successfully assigning delivery"""
        mock_manager = create_mock_user(ID=99, user_type="manager")
        mock_delivery = create_mock_user(ID=2, user_type="delivery", email="delivery@test.com")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        mock_bid = create_mock_bid(id=1, deliveryPersonID=2, bidAmount=300)
        
        # Setup query mocks
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        
        # Query calls: Order, Account, Bid (for assignment), Bid (for lowest)
        order_filter = MagicMock()
        order_filter.first.return_value = mock_order
        
        delivery_filter = MagicMock()
        delivery_filter.first.return_value = mock_delivery
        
        bid_filter = MagicMock()
        bid_filter.first.return_value = mock_bid
        
        # For lowest bid check - same bid is lowest
        lowest_bid_filter = MagicMock()
        lowest_bid_filter.order_by.return_value.first.return_value = mock_bid
        
        query_mock.filter.side_effect = [order_filter, delivery_filter, bid_filter, lowest_bid_filter]
        
        app.dependency_overrides[require_manager] = lambda: mock_manager
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders/1/assign", json={
                "delivery_id": 2
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Delivery assigned successfully"
            assert data["order_id"] == 1
            assert data["assigned_delivery_id"] == 2
            assert data["order_status"] == "assigned"
            assert data["is_lowest_bid"] == True
        finally:
            app.dependency_overrides.clear()

    def test_assign_delivery_non_manager_forbidden(self):
        """Test that non-managers cannot assign delivery"""
        mock_user = create_mock_user(user_type="customer")
        mock_db = create_mock_db()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders/1/assign", json={
                "delivery_id": 2
            })
            
            # Should be 403 (require_manager dependency rejects)
            assert response.status_code in [401, 403]
        finally:
            app.dependency_overrides.clear()

    def test_assign_delivery_no_bid_rejected(self):
        """Test that assignment fails if delivery person has no bid"""
        mock_manager = create_mock_user(ID=99, user_type="manager")
        mock_delivery = create_mock_user(ID=2, user_type="delivery")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        
        order_filter = MagicMock()
        order_filter.first.return_value = mock_order
        
        delivery_filter = MagicMock()
        delivery_filter.first.return_value = mock_delivery
        
        bid_filter = MagicMock()
        bid_filter.first.return_value = None  # No bid found
        
        query_mock.filter.side_effect = [order_filter, delivery_filter, bid_filter]
        
        app.dependency_overrides[require_manager] = lambda: mock_manager
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders/1/assign", json={
                "delivery_id": 2
            })
            
            assert response.status_code == 400
            assert "not submitted a bid" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Transaction Audit Tests
# ============================================================

class TestTransactionAudit:
    """Test transaction audit logging"""

    def test_order_creates_transaction_log(self):
        """Test that order creation creates a transaction audit entry"""
        mock_user = create_mock_user(balance=10000)
        mock_db = create_mock_db()
        mock_dish = create_mock_dish(id=1, cost=1000)
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_dish]
        
        transactions_created = []
        orders_created = []
        
        def capture_add(obj):
            if hasattr(obj, 'transaction_type'):
                transactions_created.append(obj)
            elif hasattr(obj, 'finalCost'):
                obj.id = 1
                orders_created.append(obj)
        
        mock_db.add.side_effect = capture_add
        mock_db.flush.side_effect = lambda: None
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders", json={
                "items": [{"dish_id": 1, "qty": 1}],
                "delivery_address": "123 Test Street"
            })
            
            assert response.status_code == 201
            
            # Verify transaction was logged
            assert len(transactions_created) == 1
            tx = transactions_created[0]
            assert tx.transaction_type == "order_payment"
            assert tx.amount_cents < 0  # Debit
            assert tx.reference_type == "order"
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Edge Cases Tests
# ============================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_order_exact_balance(self):
        """Test order when user has exactly the required amount"""
        mock_user = create_mock_user(balance=1500)  # Exactly $15 (dish $10 + delivery $5)
        mock_db = create_mock_db()
        mock_dish = create_mock_dish(id=1, cost=1000)
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_dish]
        
        created_order = None
        def capture_add(obj):
            nonlocal created_order
            if hasattr(obj, 'finalCost'):
                created_order = obj
                obj.id = 1
        mock_db.add.side_effect = capture_add
        mock_db.flush.side_effect = lambda: setattr(created_order, 'id', 1) if created_order else None
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders", json={
                "items": [{"dish_id": 1, "qty": 1}],
                "delivery_address": "123 Test Street"
            })
            
            assert response.status_code == 201
            data = response.json()
            assert data["new_balance"] == 0  # Should have exactly $0 left
        finally:
            app.dependency_overrides.clear()

    def test_order_1_cent_short(self):
        """Test order when user is 1 cent short"""
        mock_user = create_mock_user(balance=1499, warnings=0)  # $14.99, need $15
        mock_db = create_mock_db()
        mock_dish = create_mock_dish(id=1, cost=1000)
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_dish]
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders", json={
                "items": [{"dish_id": 1, "qty": 1}],
                "delivery_address": "123 Test Street"
            })
            
            assert response.status_code == 402
            data = response.json()
            assert data["detail"]["shortfall"] == 1  # 1 cent short
            assert mock_user.warnings == 1
        finally:
            app.dependency_overrides.clear()

    def test_multiple_items_order(self):
        """Test order with multiple different items"""
        mock_user = create_mock_user(balance=50000)
        mock_db = create_mock_db()
        mock_dish1 = create_mock_dish(id=1, name="Dish 1", cost=1000)
        mock_dish2 = create_mock_dish(id=2, name="Dish 2", cost=2000)
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_dish1, mock_dish2]
        
        created_order = None
        def capture_add(obj):
            nonlocal created_order
            if hasattr(obj, 'finalCost'):
                created_order = obj
                obj.id = 1
        mock_db.add.side_effect = capture_add
        mock_db.flush.side_effect = lambda: setattr(created_order, 'id', 1) if created_order else None
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders", json={
                "items": [
                    {"dish_id": 1, "qty": 2},  # 2 * $10 = $20
                    {"dish_id": 2, "qty": 1}   # 1 * $20 = $20
                ],
                "delivery_address": "123 Test Street"
            })
            
            assert response.status_code == 201
            data = response.json()
            # Subtotal: $40, Delivery: $5, Total: $45
            assert data["order"]["subtotal_cents"] == 4000
            assert data["order"]["finalCost"] == 4500
        finally:
            app.dependency_overrides.clear()

    def test_warning_accumulation(self):
        """Test that warnings accumulate on repeated insufficient deposit attempts"""
        mock_user = create_mock_user(balance=100, warnings=2)  # Already 2 warnings
        mock_db = create_mock_db()
        mock_dish = create_mock_dish(id=1, cost=1000)
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_dish]
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders", json={
                "items": [{"dish_id": 1, "qty": 1}],
                "delivery_address": "123 Test Street"
            })
            
            assert response.status_code == 402
            data = response.json()
            assert data["detail"]["warnings"] == 3  # Incremented from 2 to 3
            assert mock_user.warnings == 3
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Authorization Tests
# ============================================================

class TestAuthorization:
    """Test authorization for various endpoints"""

    def test_order_requires_auth(self):
        """Test that POST /orders requires authentication"""
        response = client.post("/orders", json={
            "items": [{"dish_id": 1, "qty": 1}],
            "delivery_address": "123 Test Street"
        })
        
        assert response.status_code == 401

    def test_get_order_requires_auth(self):
        """Test that GET /orders/{id} requires authentication"""
        response = client.get("/orders/1")
        
        assert response.status_code == 401

    def test_bid_requires_auth(self):
        """Test that POST /orders/{id}/bid requires authentication"""
        response = client.post("/orders/1/bid", json={
            "price_cents": 300
        })
        
        assert response.status_code == 401

    def test_list_bids_requires_auth(self):
        """Test that GET /orders/{id}/bids requires authentication"""
        response = client.get("/orders/1/bids")
        
        assert response.status_code == 401

    def test_assign_requires_auth(self):
        """Test that POST /orders/{id}/assign requires authentication"""
        response = client.post("/orders/1/assign", json={
            "delivery_id": 2
        })
        
        assert response.status_code == 401
