"""
Tests for delivery person workflows
Covers:
- GET /delivery/available-orders - Orders open for bidding
- POST /delivery/orders/{id}/bid - Place bid with throttling and deadline
- GET /delivery/my-bids - List user's bids
- GET /delivery/assigned - Get assigned orders
- POST /delivery/orders/{id}/mark-delivered - Mark as delivered
- GET /delivery/history - Delivery history with ratings
- GET /delivery/stats - Aggregate stats
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.main import app
from app.auth import get_current_user
from app.database import get_db
from app.models import Account, Order, Bid, DeliveryRating, OrderDeliveryReview


client = TestClient(app)


# ============================================================
# Mock Factories
# ============================================================

def create_mock_delivery_user(ID=10, email="delivery@test.com", warnings=0):
    """Create a mock delivery person user"""
    mock_user = MagicMock(spec=Account)
    mock_user.ID = ID
    mock_user.email = email
    mock_user.type = "delivery"
    mock_user.balance = 0
    mock_user.warnings = warnings
    mock_user.wage = None
    mock_user.restaurantID = 1
    return mock_user


def create_mock_customer_user(ID=5, email="customer@test.com"):
    """Create a mock customer user"""
    mock_user = MagicMock(spec=Account)
    mock_user.ID = ID
    mock_user.email = email
    mock_user.type = "customer"
    mock_user.balance = 10000
    mock_user.warnings = 0
    mock_user.wage = None
    mock_user.restaurantID = 1
    return mock_user


def create_mock_order(
    id=1,
    accountID=5,
    status="paid",
    bidID=None,
    bidding_closes_at=None,
    delivered_at=None
):
    """Create a mock order"""
    mock_order = MagicMock(spec=Order)
    mock_order.id = id
    mock_order.accountID = accountID
    mock_order.dateTime = datetime.now(timezone.utc).isoformat()
    mock_order.finalCost = 2500
    mock_order.status = status
    mock_order.bidID = bidID
    mock_order.note = "Test order"
    mock_order.delivery_address = "123 Test St"
    mock_order.delivery_fee = 500
    mock_order.subtotal_cents = 2000
    mock_order.discount_cents = 0
    mock_order.free_delivery_used = 0
    mock_order.assignment_memo = None
    mock_order.bidding_closes_at = bidding_closes_at
    mock_order.delivered_at = delivered_at
    mock_order.ordered_dishes = []
    
    # Create mock customer account
    mock_customer = create_mock_customer_user(ID=accountID)
    mock_order.account = mock_customer
    
    return mock_order


def create_mock_bid(
    id=1,
    deliveryPersonID=10,
    orderID=1,
    bidAmount=300,
    estimated_minutes=30,
    created_at=None
):
    """Create a mock bid"""
    mock_bid = MagicMock(spec=Bid)
    mock_bid.id = id
    mock_bid.deliveryPersonID = deliveryPersonID
    mock_bid.orderID = orderID
    mock_bid.bidAmount = bidAmount
    mock_bid.estimated_minutes = estimated_minutes
    mock_bid.created_at = created_at or datetime.now(timezone.utc).isoformat()
    mock_bid.delivery_person = create_mock_delivery_user(ID=deliveryPersonID)
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
# GET /delivery/available-orders Tests
# ============================================================

class TestAvailableOrders:
    """Test GET /delivery/available-orders endpoint"""

    def test_get_available_orders_success(self):
        """Test getting orders available for bidding"""
        mock_user = create_mock_delivery_user()
        mock_db = create_mock_db()
        mock_order = create_mock_order(status="paid")
        
        # Setup query chain
        orders_query = MagicMock()
        orders_query.options.return_value = orders_query
        orders_query.filter.return_value = orders_query
        orders_query.count.return_value = 1
        orders_query.order_by.return_value = orders_query
        orders_query.offset.return_value = orders_query
        orders_query.limit.return_value = orders_query
        orders_query.all.return_value = [mock_order]
        
        bid_query = MagicMock()
        bid_query.filter.return_value = bid_query
        bid_query.first.return_value = None
        bid_query.count.return_value = 0
        bid_query.order_by.return_value = bid_query
        
        def query_side_effect(model):
            if model is Order:
                return orders_query
            elif model is Bid:
                return bid_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/delivery/available-orders")
            
            assert response.status_code == 200
            data = response.json()
            assert "orders" in data
            assert data["total"] >= 0
        finally:
            app.dependency_overrides.clear()

    def test_requires_delivery_person(self):
        """Test that non-delivery users are rejected"""
        mock_user = create_mock_customer_user()
        mock_db = create_mock_db()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/delivery/available-orders")
            
            assert response.status_code == 403
            assert "delivery personnel" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


# ============================================================
# POST /delivery/orders/{id}/bid Tests
# ============================================================

class TestPlaceBid:
    """Test POST /delivery/orders/{id}/bid endpoint"""

    def test_place_bid_success(self):
        """Test successful bid placement"""
        mock_user = create_mock_delivery_user()
        mock_db = create_mock_db()
        mock_order = create_mock_order(status="paid")
        
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        existing_bid_query = MagicMock()
        existing_bid_query.filter.return_value.first.return_value = None
        
        last_bid_query = MagicMock()
        last_bid_query.filter.return_value.order_by.return_value.first.return_value = None
        
        lowest_bid_query = MagicMock()
        lowest_bid_query.filter.return_value.order_by.return_value.first.return_value = None
        
        call_count = [0]
        def query_side_effect(model):
            call_count[0] += 1
            if model is Order:
                return order_query
            elif model is Bid:
                if call_count[0] == 2:  # Existing bid check
                    return existing_bid_query
                elif call_count[0] == 3:  # Last bid check (throttle)
                    return last_bid_query
                else:  # Lowest bid check
                    return lowest_bid_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        
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
            response = client.post("/delivery/orders/1/bid", json={
                "price_cents": 450,
                "estimated_minutes": 25
            })
            
            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
            data = response.json()
            assert data["bidAmount"] == 450
            assert data["estimated_minutes"] == 25
        finally:
            app.dependency_overrides.clear()

    def test_bid_throttle_enforced(self):
        """Test that bid throttle prevents rapid bidding"""
        mock_user = create_mock_delivery_user()
        mock_db = create_mock_db()
        mock_order = create_mock_order(status="paid")
        
        # Create a recent bid (5 seconds ago)
        recent_bid = create_mock_bid(
            created_at=(datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
        )
        
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        existing_bid_query = MagicMock()
        existing_bid_query.filter.return_value.first.return_value = None
        
        last_bid_query = MagicMock()
        last_bid_query.filter.return_value.order_by.return_value.first.return_value = recent_bid
        
        call_count = [0]
        def query_side_effect(model):
            call_count[0] += 1
            if model is Order:
                return order_query
            elif model is Bid:
                if call_count[0] == 2:
                    return existing_bid_query
                else:
                    return last_bid_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/delivery/orders/1/bid", json={
                "price_cents": 450,
                "estimated_minutes": 25
            })
            
            assert response.status_code == 429
            assert "wait" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_bid_after_deadline_rejected(self):
        """Test that bids after deadline are rejected"""
        mock_user = create_mock_delivery_user()
        mock_db = create_mock_db()
        
        # Order with bidding closed 1 hour ago
        mock_order = create_mock_order(
            status="paid",
            bidding_closes_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        )
        
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        mock_db.query.side_effect = lambda model: order_query if model is Order else MagicMock()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/delivery/orders/1/bid", json={
                "price_cents": 450,
                "estimated_minutes": 25
            })
            
            assert response.status_code == 400
            assert "closed" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_duplicate_bid_rejected(self):
        """Test that duplicate bids are rejected"""
        mock_user = create_mock_delivery_user()
        mock_db = create_mock_db()
        mock_order = create_mock_order(status="paid")
        existing_bid = create_mock_bid(deliveryPersonID=mock_user.ID)
        
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        existing_bid_query = MagicMock()
        existing_bid_query.filter.return_value.first.return_value = existing_bid
        
        call_count = [0]
        def query_side_effect(model):
            call_count[0] += 1
            if model is Order:
                return order_query
            elif model is Bid:
                return existing_bid_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/delivery/orders/1/bid", json={
                "price_cents": 450,
                "estimated_minutes": 25
            })
            
            assert response.status_code == 400
            assert "already submitted" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_bid_on_non_paid_order_rejected(self):
        """Test that bids on non-paid orders are rejected"""
        mock_user = create_mock_delivery_user()
        mock_db = create_mock_db()
        mock_order = create_mock_order(status="assigned")  # Already assigned
        
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        mock_db.query.side_effect = lambda model: order_query if model is Order else MagicMock()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/delivery/orders/1/bid", json={
                "price_cents": 450,
                "estimated_minutes": 25
            })
            
            assert response.status_code == 400
            assert "not open for bidding" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


# ============================================================
# POST /delivery/orders/{id}/mark-delivered Tests
# ============================================================

class TestMarkDelivered:
    """Test POST /delivery/orders/{id}/mark-delivered endpoint"""

    def test_mark_delivered_success(self):
        """Test successful delivery completion"""
        mock_user = create_mock_delivery_user(ID=10)
        mock_db = create_mock_db()
        
        mock_bid = create_mock_bid(id=1, deliveryPersonID=10)
        mock_order = create_mock_order(
            status="assigned",
            bidID=1
        )
        
        mock_rating = MagicMock(spec=DeliveryRating)
        mock_rating.accountID = 10
        mock_rating.averageRating = Decimal("4.5")
        mock_rating.reviews = 5
        mock_rating.total_deliveries = 10
        mock_rating.on_time_deliveries = 8
        
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        bid_query = MagicMock()
        bid_query.filter.return_value.first.return_value = mock_bid
        
        rating_query = MagicMock()
        rating_query.filter.return_value.first.return_value = mock_rating
        
        def query_side_effect(model):
            if model is Order:
                return order_query
            elif model is Bid:
                return bid_query
            elif model is DeliveryRating:
                return rating_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/delivery/orders/1/mark-delivered")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "delivered"
            assert "delivered_at" in data
        finally:
            app.dependency_overrides.clear()

    def test_mark_delivered_wrong_person_rejected(self):
        """Test that non-assigned person cannot mark delivered"""
        mock_user = create_mock_delivery_user(ID=10)
        mock_db = create_mock_db()
        
        # Bid belongs to different delivery person (ID=20)
        mock_bid = create_mock_bid(id=1, deliveryPersonID=20)
        mock_order = create_mock_order(
            status="assigned",
            bidID=1
        )
        
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        bid_query = MagicMock()
        bid_query.filter.return_value.first.return_value = mock_bid
        
        def query_side_effect(model):
            if model is Order:
                return order_query
            elif model is Bid:
                return bid_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/delivery/orders/1/mark-delivered")
            
            assert response.status_code == 403
            assert "not the assigned delivery person" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


# ============================================================
# GET /delivery/history Tests
# ============================================================

class TestDeliveryHistory:
    """Test GET /delivery/history endpoint"""

    def test_get_history_success(self):
        """Test getting delivery history"""
        mock_user = create_mock_delivery_user()
        mock_db = create_mock_db()
        
        # Setup complex query chain
        bid_ids_query = MagicMock()
        bid_ids_query.filter.return_value.subquery.return_value = MagicMock()
        
        orders_query = MagicMock()
        orders_query.options.return_value = orders_query
        orders_query.filter.return_value = orders_query
        orders_query.count.return_value = 0
        orders_query.order_by.return_value = orders_query
        orders_query.offset.return_value = orders_query
        orders_query.limit.return_value = orders_query
        orders_query.all.return_value = []
        
        def query_side_effect(model):
            if model is Bid:
                q = MagicMock()
                q.id = MagicMock()  # For subquery
                q.filter.return_value.subquery.return_value = MagicMock()
                return q
            elif model is Order:
                return orders_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/delivery/history")
            
            assert response.status_code == 200
            data = response.json()
            assert "deliveries" in data
            assert "total" in data
            assert "page" in data
        finally:
            app.dependency_overrides.clear()


# ============================================================
# GET /delivery/stats Tests
# ============================================================

class TestDeliveryStats:
    """Test GET /delivery/stats endpoint"""

    def test_get_stats_success(self):
        """Test getting delivery statistics"""
        mock_user = create_mock_delivery_user()
        mock_db = create_mock_db()
        
        mock_rating = MagicMock(spec=DeliveryRating)
        mock_rating.accountID = 10
        mock_rating.averageRating = Decimal("4.5")
        mock_rating.reviews = 15
        mock_rating.total_deliveries = 20
        mock_rating.on_time_deliveries = 18
        mock_rating.avg_delivery_minutes = 25
        
        rating_query = MagicMock()
        rating_query.filter.return_value.first.return_value = mock_rating
        
        reviews_query = MagicMock()
        reviews_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        bids_query = MagicMock()
        bids_query.filter.return_value.count.return_value = 50
        bids_query.filter.return_value.subquery.return_value = MagicMock()
        
        orders_query = MagicMock()
        orders_query.filter.return_value.count.return_value = 2
        
        call_count = [0]
        def query_side_effect(model):
            call_count[0] += 1
            if model is DeliveryRating:
                return rating_query
            elif model is OrderDeliveryReview:
                return reviews_query
            elif model is Bid:
                q = MagicMock()
                q.filter.return_value.count.return_value = 50
                q.id = MagicMock()
                q.filter.return_value.subquery.return_value = MagicMock()
                return q
            elif model is Order:
                return orders_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/delivery/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert "average_rating" in data
            assert "total_deliveries" in data
            assert "on_time_percentage" in data
            assert data["average_rating"] == 4.5
            assert data["total_deliveries"] == 20
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Integration-style Tests
# ============================================================

class TestDeliveryWorkflowIntegration:
    """Integration-style tests for delivery workflow"""

    def test_customer_cannot_access_delivery_endpoints(self):
        """Verify customers cannot access delivery-only endpoints"""
        mock_user = create_mock_customer_user()
        mock_db = create_mock_db()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            endpoints = [
                ("GET", "/delivery/available-orders"),
                ("GET", "/delivery/my-bids"),
                ("GET", "/delivery/assigned"),
                ("GET", "/delivery/history"),
                ("GET", "/delivery/stats"),
            ]
            
            for method, endpoint in endpoints:
                if method == "GET":
                    response = client.get(endpoint)
                else:
                    response = client.post(endpoint)
                
                assert response.status_code == 403, f"{method} {endpoint} should reject customer"
        finally:
            app.dependency_overrides.clear()
