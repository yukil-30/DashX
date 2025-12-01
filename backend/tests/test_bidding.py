"""
Tests for delivery bidding functionality
Covers:
- POST /bids - Create bid with order_id in body
- GET /orders/{id}/bids - List bids with stats
- POST /orders/{id}/assign - Manager assignment
- Lowest bid detection
- Memo requirement when non-lowest bid chosen
- Delivery person stats (on-time %, ratings)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timezone
from decimal import Decimal

from app.main import app
from app.auth import create_access_token, get_current_user, require_manager
from app.database import get_db
from app.models import Account, Order, Bid, DeliveryRating


client = TestClient(app)


# ============================================================
# Mock Factories
# ============================================================

def create_mock_user(
    ID=1,
    email="user@example.com",
    balance=10000,
    user_type="customer",
    warnings=0
):
    """Create a mock user for testing"""
    mock_user = MagicMock(spec=Account)
    mock_user.ID = ID
    mock_user.email = email
    mock_user.type = user_type
    mock_user.balance = balance
    mock_user.warnings = warnings
    mock_user.wage = None
    mock_user.restaurantID = 1
    return mock_user


def create_mock_order(
    id=1,
    accountID=1,
    status="paid",
    bidID=None,
    assignment_memo=None
):
    """Create a mock order"""
    mock_order = MagicMock(spec=Order)
    mock_order.id = id
    mock_order.accountID = accountID
    mock_order.dateTime = datetime.now(timezone.utc).isoformat()
    mock_order.finalCost = 2500
    mock_order.status = status
    mock_order.bidID = bidID
    mock_order.note = None
    mock_order.delivery_address = "123 Test St"
    mock_order.delivery_fee = 500
    mock_order.subtotal_cents = 2000
    mock_order.discount_cents = 0
    mock_order.free_delivery_used = 0
    mock_order.assignment_memo = assignment_memo
    mock_order.ordered_dishes = []
    return mock_order


def create_mock_bid(id=1, deliveryPersonID=2, orderID=1, bidAmount=300, estimated_minutes=30):
    """Create a mock bid"""
    mock_bid = MagicMock(spec=Bid)
    mock_bid.id = id
    mock_bid.deliveryPersonID = deliveryPersonID
    mock_bid.orderID = orderID
    mock_bid.bidAmount = bidAmount
    mock_bid.estimated_minutes = estimated_minutes
    mock_bid.delivery_person = create_mock_user(
        ID=deliveryPersonID,
        email=f"delivery{deliveryPersonID}@example.com",
        user_type="delivery"
    )
    return mock_bid


def create_mock_delivery_rating(
    accountID=2,
    averageRating=4.5,
    reviews=10,
    total_deliveries=50,
    on_time_deliveries=45,
    avg_delivery_minutes=25
):
    """Create a mock delivery rating"""
    mock_rating = MagicMock(spec=DeliveryRating)
    mock_rating.accountID = accountID
    mock_rating.averageRating = Decimal(str(averageRating))
    mock_rating.reviews = reviews
    mock_rating.total_deliveries = total_deliveries
    mock_rating.on_time_deliveries = on_time_deliveries
    mock_rating.avg_delivery_minutes = avg_delivery_minutes
    return mock_rating


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
# POST /bids Tests
# ============================================================

class TestCreateBidStandalone:
    """Test POST /bids endpoint"""

    def test_create_bid_success(self):
        """Test delivery person creating a bid via POST /bids"""
        mock_user = create_mock_user(ID=2, email="delivery@test.com", user_type="delivery")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        
        # Setup query chain
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        bid_query = MagicMock()
        bid_query.filter.return_value.first.return_value = None  # No existing bid
        
        lowest_bid_query = MagicMock()
        lowest_bid_query.filter.return_value.order_by.return_value.first.return_value = None
        
        call_count = [0]
        def query_side_effect(model):
            call_count[0] += 1
            if model == Order:
                return order_query
            elif model == Bid:
                if call_count[0] <= 2:
                    return bid_query
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
            response = client.post("/bids", json={
                "order_id": 1,
                "price_cents": 350,
                "estimated_minutes": 25
            })
            
            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
            data = response.json()
            assert data["bidAmount"] == 350
            assert data["estimated_minutes"] == 25
            assert data["deliveryPersonID"] == 2
            assert data["orderID"] == 1
        finally:
            app.dependency_overrides.clear()

    def test_create_bid_missing_order_id(self):
        """Test bid creation fails without order_id"""
        mock_user = create_mock_user(ID=2, user_type="delivery")
        mock_db = create_mock_db()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/bids", json={
                "price_cents": 350
            })
            
            assert response.status_code == 400
            assert "order_id" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_create_bid_non_delivery_forbidden(self):
        """Test that non-delivery personnel cannot bid"""
        mock_user = create_mock_user(user_type="customer")
        mock_db = create_mock_db()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/bids", json={
                "order_id": 1,
                "price_cents": 350
            })
            
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Lowest Bid Detection Tests
# ============================================================

class TestLowestBidDetection:
    """Test that lowest bid is correctly identified"""

    def test_lowest_bid_marked_correctly(self):
        """Test that bids are correctly marked as lowest"""
        mock_user = create_mock_user(ID=1, user_type="manager")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        
        # Create bids with different amounts
        mock_bid1 = create_mock_bid(id=1, deliveryPersonID=2, bidAmount=500, estimated_minutes=30)
        mock_bid2 = create_mock_bid(id=2, deliveryPersonID=3, bidAmount=300, estimated_minutes=25)  # Lowest
        mock_bid3 = create_mock_bid(id=3, deliveryPersonID=4, bidAmount=400, estimated_minutes=20)
        
        # Setup query chain
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        bids_query = MagicMock()
        # Return sorted by amount (lowest first)
        bids_query.options.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_bid2, mock_bid3, mock_bid1  # Sorted by bidAmount
        ]
        
        rating_query = MagicMock()
        mock_rating = create_mock_delivery_rating(accountID=2)
        rating_query.filter.return_value.first.return_value = mock_rating
        
        def query_side_effect(model):
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
            assert data["lowest_bid_id"] == 2  # bid2 is lowest at 300
            
            # Find the lowest bid in the response
            bids = data["bids"]
            assert len(bids) == 3
            
            # First bid should be lowest (sorted by amount)
            assert bids[0]["is_lowest"] == True
            assert bids[0]["bidAmount"] == 300
            
            # Other bids should not be lowest
            assert bids[1]["is_lowest"] == False
            assert bids[2]["is_lowest"] == False
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Manager Assignment Tests
# ============================================================

class TestManagerAssignment:
    """Test POST /orders/{id}/assign endpoint"""

    def test_assign_lowest_bid_success(self):
        """Test assigning lowest bid - no memo required"""
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
        
        lowest_bid_filter = MagicMock()
        lowest_bid_filter.order_by.return_value.first.return_value = mock_bid  # Same bid is lowest
        
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
            assert data["is_lowest_bid"] == True
            assert data["memo_saved"] == False
            assert data["order_status"] == "assigned"
        finally:
            app.dependency_overrides.clear()

    def test_assign_non_lowest_bid_requires_memo(self):
        """Test that assigning non-lowest bid requires memo"""
        mock_manager = create_mock_user(ID=99, user_type="manager")
        mock_delivery = create_mock_user(ID=3, user_type="delivery", email="delivery3@test.com")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        
        # This bid (400) is not the lowest
        mock_bid = create_mock_bid(id=2, deliveryPersonID=3, bidAmount=400)
        # Lowest bid is 300
        mock_lowest_bid = create_mock_bid(id=1, deliveryPersonID=2, bidAmount=300)
        
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        
        order_filter = MagicMock()
        order_filter.first.return_value = mock_order
        
        delivery_filter = MagicMock()
        delivery_filter.first.return_value = mock_delivery
        
        bid_filter = MagicMock()
        bid_filter.first.return_value = mock_bid
        
        lowest_bid_filter = MagicMock()
        lowest_bid_filter.order_by.return_value.first.return_value = mock_lowest_bid  # Different bid is lowest
        
        query_mock.filter.side_effect = [order_filter, delivery_filter, bid_filter, lowest_bid_filter]
        
        app.dependency_overrides[require_manager] = lambda: mock_manager
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            # Try to assign without memo
            response = client.post("/orders/1/assign", json={
                "delivery_id": 3
            })
            
            assert response.status_code == 400
            assert "memo is required" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_assign_non_lowest_bid_with_memo_success(self):
        """Test that assigning non-lowest bid succeeds with memo"""
        mock_manager = create_mock_user(ID=99, user_type="manager")
        mock_delivery = create_mock_user(ID=3, user_type="delivery", email="delivery3@test.com")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        
        # This bid (400) is not the lowest
        mock_bid = create_mock_bid(id=2, deliveryPersonID=3, bidAmount=400)
        # Lowest bid is 300
        mock_lowest_bid = create_mock_bid(id=1, deliveryPersonID=2, bidAmount=300)
        
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        
        order_filter = MagicMock()
        order_filter.first.return_value = mock_order
        
        delivery_filter = MagicMock()
        delivery_filter.first.return_value = mock_delivery
        
        bid_filter = MagicMock()
        bid_filter.first.return_value = mock_bid
        
        lowest_bid_filter = MagicMock()
        lowest_bid_filter.order_by.return_value.first.return_value = mock_lowest_bid
        
        query_mock.filter.side_effect = [order_filter, delivery_filter, bid_filter, lowest_bid_filter]
        
        app.dependency_overrides[require_manager] = lambda: mock_manager
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/orders/1/assign", json={
                "delivery_id": 3,
                "memo": "Chosen for better reliability and on-time record"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Delivery assigned successfully"
            assert data["is_lowest_bid"] == False
            assert data["memo_saved"] == True
            
            # Verify memo was saved to order
            assert mock_order.assignment_memo == "Chosen for better reliability and on-time record"
        finally:
            app.dependency_overrides.clear()

    def test_assign_non_lowest_bid_empty_memo_rejected(self):
        """Test that empty/whitespace memo is rejected for non-lowest bid"""
        mock_manager = create_mock_user(ID=99, user_type="manager")
        mock_delivery = create_mock_user(ID=3, user_type="delivery")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        
        mock_bid = create_mock_bid(id=2, deliveryPersonID=3, bidAmount=400)
        mock_lowest_bid = create_mock_bid(id=1, deliveryPersonID=2, bidAmount=300)
        
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        
        order_filter = MagicMock()
        order_filter.first.return_value = mock_order
        
        delivery_filter = MagicMock()
        delivery_filter.first.return_value = mock_delivery
        
        bid_filter = MagicMock()
        bid_filter.first.return_value = mock_bid
        
        lowest_bid_filter = MagicMock()
        lowest_bid_filter.order_by.return_value.first.return_value = mock_lowest_bid
        
        query_mock.filter.side_effect = [order_filter, delivery_filter, bid_filter, lowest_bid_filter]
        
        app.dependency_overrides[require_manager] = lambda: mock_manager
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            # Try with whitespace-only memo
            response = client.post("/orders/1/assign", json={
                "delivery_id": 3,
                "memo": "   "
            })
            
            assert response.status_code == 400
            assert "memo is required" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Delivery Stats Tests
# ============================================================

class TestDeliveryStats:
    """Test delivery person stats in bids response"""

    def test_bids_include_delivery_stats(self):
        """Test that bids response includes delivery person stats"""
        mock_user = create_mock_user(ID=1, user_type="manager")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        
        mock_bid = create_mock_bid(id=1, deliveryPersonID=2, bidAmount=300, estimated_minutes=25)
        
        mock_rating = create_mock_delivery_rating(
            accountID=2,
            averageRating=4.7,
            reviews=25,
            total_deliveries=100,
            on_time_deliveries=92,
            avg_delivery_minutes=22
        )
        
        # Setup query chain
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        bids_query = MagicMock()
        bids_query.options.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_bid]
        
        rating_query = MagicMock()
        rating_query.filter.return_value.first.return_value = mock_rating
        
        def query_side_effect(model):
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
            
            assert len(data["bids"]) == 1
            bid = data["bids"][0]
            
            # Check delivery person stats
            stats = bid["delivery_person"]
            assert stats["average_rating"] == 4.7
            assert stats["reviews"] == 25
            assert stats["total_deliveries"] == 100
            assert stats["on_time_deliveries"] == 92
            assert stats["on_time_percentage"] == 92.0  # 92/100 * 100
            assert stats["avg_delivery_minutes"] == 22
        finally:
            app.dependency_overrides.clear()

    def test_on_time_percentage_calculated_correctly(self):
        """Test on-time percentage calculation"""
        mock_user = create_mock_user(ID=1, user_type="manager")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        
        mock_bid = create_mock_bid(id=1, deliveryPersonID=2, bidAmount=300)
        
        # 45 on-time out of 50 total = 90%
        mock_rating = create_mock_delivery_rating(
            accountID=2,
            total_deliveries=50,
            on_time_deliveries=45
        )
        
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        bids_query = MagicMock()
        bids_query.options.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_bid]
        
        rating_query = MagicMock()
        rating_query.filter.return_value.first.return_value = mock_rating
        
        def query_side_effect(model):
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
            
            stats = data["bids"][0]["delivery_person"]
            assert stats["on_time_percentage"] == 90.0
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Scoreboard Tests
# ============================================================

class TestDeliveryScoreboard:
    """Test GET /bids/scoreboard endpoint"""

    def test_scoreboard_returns_delivery_stats(self):
        """Test scoreboard returns all delivery personnel with stats"""
        mock_manager = create_mock_user(ID=99, user_type="manager")
        mock_db = create_mock_db()
        
        # Create delivery accounts
        delivery1 = create_mock_user(ID=2, email="d1@test.com", user_type="delivery", warnings=0)
        delivery2 = create_mock_user(ID=3, email="d2@test.com", user_type="delivery", warnings=1)
        
        rating1 = create_mock_delivery_rating(
            accountID=2, averageRating=4.8, reviews=50,
            total_deliveries=100, on_time_deliveries=95, avg_delivery_minutes=20
        )
        rating2 = create_mock_delivery_rating(
            accountID=3, averageRating=4.2, reviews=30,
            total_deliveries=60, on_time_deliveries=50, avg_delivery_minutes=28
        )
        
        accounts_query = MagicMock()
        accounts_query.filter.return_value.all.return_value = [delivery1, delivery2]
        
        # Return different ratings based on accountID
        def rating_filter_side_effect(condition):
            result = MagicMock()
            # Check which account is being queried
            if hasattr(condition, 'right') and condition.right.value == 2:
                result.first.return_value = rating1
            elif hasattr(condition, 'right') and condition.right.value == 3:
                result.first.return_value = rating2
            else:
                result.first.return_value = rating1  # Default
            return result
        
        rating_query = MagicMock()
        rating_query.filter.side_effect = rating_filter_side_effect
        
        call_count = [0]
        def query_side_effect(model):
            call_count[0] += 1
            if model == Account:
                return accounts_query
            elif model == DeliveryRating:
                return rating_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        
        app.dependency_overrides[require_manager] = lambda: mock_manager
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/bids/scoreboard")
            
            assert response.status_code == 200
            data = response.json()
            
            assert len(data) >= 1  # At least one delivery person
        finally:
            app.dependency_overrides.clear()

    def test_scoreboard_requires_manager(self):
        """Test that scoreboard is manager-only"""
        mock_user = create_mock_user(user_type="customer")
        mock_db = create_mock_db()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/bids/scoreboard")
            
            # Should be 403 (require_manager dependency rejects)
            assert response.status_code in [401, 403]
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Edge Cases
# ============================================================

class TestEdgeCases:
    """Test edge cases for bidding"""

    def test_single_bid_is_always_lowest(self):
        """Test that a single bid is marked as lowest"""
        mock_user = create_mock_user(ID=1, user_type="manager")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        
        mock_bid = create_mock_bid(id=1, deliveryPersonID=2, bidAmount=500)
        mock_rating = create_mock_delivery_rating(accountID=2)
        
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        bids_query = MagicMock()
        bids_query.options.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_bid]
        
        rating_query = MagicMock()
        rating_query.filter.return_value.first.return_value = mock_rating
        
        def query_side_effect(model):
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
            
            assert data["lowest_bid_id"] == 1
            assert data["bids"][0]["is_lowest"] == True
        finally:
            app.dependency_overrides.clear()

    def test_no_bids_returns_empty_list(self):
        """Test that order with no bids returns empty list"""
        mock_user = create_mock_user(ID=1, user_type="manager")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        bids_query = MagicMock()
        bids_query.options.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        def query_side_effect(model):
            if model == Order:
                return order_query
            elif model == Bid:
                return bids_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/orders/1/bids")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["bids"] == []
            assert data["lowest_bid_id"] is None
        finally:
            app.dependency_overrides.clear()

    def test_tied_lowest_bids(self):
        """Test handling of tied lowest bid amounts"""
        mock_user = create_mock_user(ID=1, user_type="manager")
        mock_db = create_mock_db()
        mock_order = create_mock_order(id=1, status="paid")
        
        # Two bids with same lowest amount
        mock_bid1 = create_mock_bid(id=1, deliveryPersonID=2, bidAmount=300)
        mock_bid2 = create_mock_bid(id=2, deliveryPersonID=3, bidAmount=300)  # Same amount
        
        mock_rating = create_mock_delivery_rating(accountID=2)
        
        order_query = MagicMock()
        order_query.filter.return_value.first.return_value = mock_order
        
        bids_query = MagicMock()
        # First bid is returned first (would be first in DB order)
        bids_query.options.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_bid1, mock_bid2
        ]
        
        rating_query = MagicMock()
        rating_query.filter.return_value.first.return_value = mock_rating
        
        def query_side_effect(model):
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
            
            # First bid (by order) should be marked as lowest
            assert data["lowest_bid_id"] == 1
            assert data["bids"][0]["is_lowest"] == True
            assert data["bids"][1]["is_lowest"] == False  # Second tie is not marked
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Authorization Tests
# ============================================================

class TestBiddingAuthorization:
    """Test authorization for bidding endpoints"""

    def test_bids_endpoint_requires_auth(self):
        """Test that POST /bids requires authentication"""
        response = client.post("/bids", json={
            "order_id": 1,
            "price_cents": 300
        })
        
        assert response.status_code == 401

    def test_scoreboard_requires_auth(self):
        """Test that GET /bids/scoreboard requires authentication"""
        response = client.get("/bids/scoreboard")
        
        assert response.status_code == 401
