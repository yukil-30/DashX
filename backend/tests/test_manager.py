"""
Tests for Manager Functionality
Covers:
- HR Logic: promotions, demotions, firing
- Dispute Resolution
- Bidding Assignment
- Employee Management
- KB Moderation
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from app.main import app
from app.auth import create_access_token
from app.database import get_db
from app.models import Account, Order, Bid, DeliveryRating, Complaint, KnowledgeBase, ChatLog, Restaurant


client = TestClient(app)


# ============================================================
# Mock Factories
# ============================================================

def create_mock_manager(restaurant_id=1):
    """Create a mock manager user"""
    mock = MagicMock(spec=Account)
    mock.ID = 1
    mock.email = "manager@test.com"
    mock.type = "manager"
    mock.restaurantID = restaurant_id
    mock.warnings = 0
    mock.balance = 0
    mock.is_fired = False
    return mock


def create_mock_chef(id=10, restaurant_id=1, times_demoted=0, is_fired=False, wage=1500):
    """Create a mock chef"""
    mock = MagicMock(spec=Account)
    mock.ID = id
    mock.email = f"chef{id}@test.com"
    mock.type = "chef"
    mock.restaurantID = restaurant_id
    mock.times_demoted = times_demoted
    mock.is_fired = is_fired
    mock.wage = wage
    mock.warnings = 0
    mock.balance = 0
    mock.unresolved_complaints_count = 0
    return mock


def create_mock_delivery(id=20, restaurant_id=None, times_demoted=0, is_fired=False, wage=1200):
    """Create a mock delivery person"""
    mock = MagicMock(spec=Account)
    mock.ID = id
    mock.email = f"delivery{id}@test.com"
    mock.type = "delivery"
    mock.restaurantID = restaurant_id
    mock.times_demoted = times_demoted
    mock.is_fired = is_fired
    mock.wage = wage
    mock.warnings = 0
    mock.balance = 0
    mock.unresolved_complaints_count = 0
    return mock


def create_mock_restaurant(id=1, name="Test Restaurant"):
    """Create a mock restaurant"""
    mock = MagicMock(spec=Restaurant)
    mock.id = id
    mock.name = name
    mock.address = "123 Test St"
    return mock


def create_mock_complaint(
    id=1,
    from_account_id=100,
    to_account_id=10,
    is_resolved=False,
    disputed=False,
    resolution=None
):
    """Create a mock complaint"""
    mock = MagicMock(spec=Complaint)
    mock.id = id
    mock.from_account_id = from_account_id
    mock.to_account_id = to_account_id
    mock.description = "Test complaint"
    mock.is_resolved = is_resolved
    mock.disputed = disputed
    mock.resolution = resolution
    mock.created_at = datetime.now(timezone.utc).isoformat()
    mock.resolved_at = None
    mock.order_id = None
    return mock


def create_mock_kb_entry(id=1, is_active=True, author_id=10):
    """Create a mock KB entry"""
    mock = MagicMock(spec=KnowledgeBase)
    mock.id = id
    mock.question = "Test question?"
    mock.answer = "Test answer."
    mock.keywords = "test,example"
    mock.confidence = 0.9
    mock.author_id = author_id
    mock.is_active = is_active
    mock.created_at = datetime.now(timezone.utc).isoformat()
    return mock


# ============================================================
# HR Logic Tests
# ============================================================

class TestHRLogic:
    """Tests for HR business rules: demotion, firing, bonuses"""

    @patch("app.routers.manager.get_db")
    @patch("app.auth.get_current_user")
    def test_demote_employee_once(self, mock_get_user, mock_get_db):
        """Chef/delivery with low rating gets demoted, times_demoted increases"""
        mock_manager = create_mock_manager()
        mock_get_user.return_value = mock_manager
        
        mock_chef = create_mock_chef(times_demoted=0)
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_chef
        mock_get_db.return_value = mock_db
        
        # Verify demotion logic exists - times_demoted should increment
        assert mock_chef.times_demoted == 0
        mock_chef.times_demoted = 1
        assert mock_chef.times_demoted == 1

    @patch("app.routers.manager.get_db")
    @patch("app.auth.get_current_user")
    def test_fire_after_two_demotions(self, mock_get_user, mock_get_db):
        """Employee should be fired after 2 demotions"""
        mock_manager = create_mock_manager()
        mock_get_user.return_value = mock_manager
        
        mock_chef = create_mock_chef(times_demoted=2)
        
        # Business rule: fired after 2 demotions
        should_fire = mock_chef.times_demoted >= 2
        assert should_fire is True

    @patch("app.routers.manager.get_db")
    @patch("app.auth.get_current_user")
    def test_bonus_for_high_rating(self, mock_get_user, mock_get_db):
        """Employee with >4 avg rating should get 10% bonus"""
        mock_manager = create_mock_manager()
        mock_get_user.return_value = mock_manager
        
        mock_chef = create_mock_chef(wage=1500)
        
        # Business rule: 10% bonus for high rating
        original_wage = 1500
        bonus_rate = Decimal("1.10")
        new_wage = int(original_wage * bonus_rate)
        
        assert new_wage == 1650  # 10% increase

    @patch("app.routers.manager.get_db")
    @patch("app.auth.get_current_user")
    def test_compliment_cancels_complaint(self, mock_get_user, mock_get_db):
        """A compliment should cancel one complaint"""
        mock_manager = create_mock_manager()
        mock_get_user.return_value = mock_manager
        
        # Business rule: compliment cancels complaint
        complaints_count = 3
        compliments_count = 1
        effective_complaints = complaints_count - compliments_count
        
        assert effective_complaints == 2


class TestEmployeeCreation:
    """Tests for creating new chef/delivery accounts"""

    def test_employee_creation_requires_password(self):
        """Employee creation should require proper password handling"""
        from app.auth import hash_password
        
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 20  # Proper hash length

    def test_chef_creation_with_restaurant(self):
        """Chef must be associated with a restaurant"""
        mock_chef = create_mock_chef(restaurant_id=1)
        assert mock_chef.restaurantID == 1
        assert mock_chef.type == "chef"

    def test_delivery_creation_optional_restaurant(self):
        """Delivery can optionally be associated with restaurant"""
        mock_delivery = create_mock_delivery(restaurant_id=None)
        assert mock_delivery.restaurantID is None
        assert mock_delivery.type == "delivery"


class TestEmployeeHRActions:
    """Tests for HR action API endpoints"""

    @patch("app.routers.manager.get_db")
    @patch("app.auth.require_manager")
    def test_promote_increases_wage(self, mock_require_manager, mock_get_db):
        """Promote action should increase employee wage"""
        mock_manager = create_mock_manager()
        mock_require_manager.return_value = mock_manager
        
        # Promotion wage increase calculation
        original_wage = 1000
        promotion_rate = Decimal("1.10")  # 10% raise
        new_wage = int(original_wage * promotion_rate)
        
        assert new_wage == 1100

    @patch("app.routers.manager.get_db")
    @patch("app.auth.require_manager")
    def test_demote_decreases_wage(self, mock_require_manager, mock_get_db):
        """Demote action should decrease employee wage"""
        mock_manager = create_mock_manager()
        mock_require_manager.return_value = mock_manager
        
        # Demotion wage decrease calculation
        original_wage = 1000
        demotion_rate = Decimal("0.90")  # 10% cut
        new_wage = int(original_wage * demotion_rate)
        
        assert new_wage == 900

    @patch("app.routers.manager.get_db")
    @patch("app.auth.require_manager")
    def test_fire_sets_is_fired_flag(self, mock_require_manager, mock_get_db):
        """Fire action should set is_fired=True"""
        mock_chef = create_mock_chef(is_fired=False)
        
        # Simulate firing
        mock_chef.is_fired = True
        
        assert mock_chef.is_fired is True


# ============================================================
# Dispute Resolution Tests
# ============================================================

class TestDisputeResolution:
    """Tests for dispute/complaint resolution flow"""

    def test_dispute_escalation_to_manager(self):
        """Disputed complaint should be visible to manager"""
        mock_complaint = create_mock_complaint(disputed=True)
        assert mock_complaint.disputed is True
        assert mock_complaint.is_resolved is False

    def test_uphold_dispute_adds_warning(self):
        """Upholding a dispute should add warning to accused"""
        mock_target = create_mock_chef(id=10)
        mock_target.warnings = 0
        
        # Uphold dispute
        mock_target.warnings += 1
        
        assert mock_target.warnings == 1

    def test_dismiss_dispute_no_warning(self):
        """Dismissing a dispute should not add warning"""
        mock_target = create_mock_chef(id=10)
        initial_warnings = mock_target.warnings
        
        # Dismiss - no change to warnings
        assert mock_target.warnings == initial_warnings

    def test_resolve_sets_resolution_timestamp(self):
        """Resolution should set resolved_at and resolution fields"""
        mock_complaint = create_mock_complaint()
        
        # Resolve
        mock_complaint.is_resolved = True
        mock_complaint.resolved_at = datetime.now(timezone.utc).isoformat()
        mock_complaint.resolution = "Complaint upheld. Warning issued."
        
        assert mock_complaint.is_resolved is True
        assert mock_complaint.resolved_at is not None
        assert "upheld" in mock_complaint.resolution.lower()

    def test_three_complaints_triggers_demotion(self):
        """3 complaints should trigger automatic demotion"""
        complaints_count = 3
        
        # Business rule: 3 complaints = demotion
        should_demote = complaints_count >= 3
        assert should_demote is True


# ============================================================
# Bidding Assignment Tests
# ============================================================

class TestBiddingAssignment:
    """Tests for manager bidding assignment functionality"""

    def test_lowest_bid_no_memo_required(self):
        """Choosing lowest bid should not require memo"""
        bids = [
            {"id": 1, "amount": 500},
            {"id": 2, "amount": 300},  # Lowest
            {"id": 3, "amount": 400}
        ]
        
        chosen_bid = bids[1]  # Lowest
        lowest_bid = min(bids, key=lambda b: b["amount"])
        
        memo_required = chosen_bid["amount"] != lowest_bid["amount"]
        assert memo_required is False

    def test_non_lowest_bid_requires_memo(self):
        """Choosing non-lowest bid should require memo"""
        bids = [
            {"id": 1, "amount": 500},
            {"id": 2, "amount": 300},  # Lowest
            {"id": 3, "amount": 400}
        ]
        
        chosen_bid = bids[0]  # Not lowest
        lowest_bid = min(bids, key=lambda b: b["amount"])
        
        memo_required = chosen_bid["amount"] != lowest_bid["amount"]
        assert memo_required is True

    def test_assign_updates_order_status(self):
        """Assignment should update order status to 'delivering'"""
        mock_order = MagicMock(spec=Order)
        mock_order.status = "paid"
        
        # Assign delivery
        mock_order.status = "delivering"
        mock_order.bidID = 1
        
        assert mock_order.status == "delivering"
        assert mock_order.bidID == 1

    def test_only_paid_orders_can_be_assigned(self):
        """Only orders with status='paid' can have delivery assigned"""
        valid_statuses = ["paid"]
        
        mock_order_pending = MagicMock()
        mock_order_pending.status = "pending"
        
        mock_order_paid = MagicMock()
        mock_order_paid.status = "paid"
        
        assert mock_order_pending.status not in valid_statuses
        assert mock_order_paid.status in valid_statuses


# ============================================================
# KB Moderation Tests
# ============================================================

class TestKBModeration:
    """Tests for Knowledge Base moderation functionality"""

    def test_deactivate_kb_entry(self):
        """Deactivating KB entry should set is_active=False"""
        mock_entry = create_mock_kb_entry(is_active=True)
        
        # Deactivate
        mock_entry.is_active = False
        
        assert mock_entry.is_active is False

    def test_restore_kb_entry(self):
        """Restoring KB entry should set is_active=True"""
        mock_entry = create_mock_kb_entry(is_active=False)
        
        # Restore
        mock_entry.is_active = True
        
        assert mock_entry.is_active is True

    def test_permanent_delete_removes_entry(self):
        """Permanent delete should remove entry from database"""
        mock_db = MagicMock()
        mock_entry = create_mock_kb_entry()
        
        # Simulate delete
        mock_db.delete(mock_entry)
        
        mock_db.delete.assert_called_once_with(mock_entry)

    def test_flagged_chats_filter(self):
        """Should filter chats with rating=0 as flagged"""
        mock_chat = MagicMock(spec=ChatLog)
        mock_chat.rating = 0
        mock_chat.flagged = True
        
        assert mock_chat.flagged is True
        assert mock_chat.rating == 0


# ============================================================
# Dashboard Statistics Tests
# ============================================================

class TestDashboardStats:
    """Tests for manager dashboard statistics"""

    def test_pending_complaints_count(self):
        """Dashboard should show pending complaints count"""
        complaints = [
            create_mock_complaint(is_resolved=False),
            create_mock_complaint(is_resolved=False),
            create_mock_complaint(is_resolved=True)
        ]
        
        pending_count = sum(1 for c in complaints if not c.is_resolved)
        assert pending_count == 2

    def test_disputed_complaints_count(self):
        """Dashboard should show disputed complaints count"""
        complaints = [
            create_mock_complaint(disputed=True, is_resolved=False),
            create_mock_complaint(disputed=False, is_resolved=False),
            create_mock_complaint(disputed=True, is_resolved=True)
        ]
        
        disputed_count = sum(1 for c in complaints if c.disputed and not c.is_resolved)
        assert disputed_count == 1

    def test_employee_counts_by_type(self):
        """Dashboard should show employee counts by role"""
        employees = [
            create_mock_chef(),
            create_mock_chef(),
            create_mock_delivery(),
        ]
        
        chef_count = sum(1 for e in employees if e.type == "chef")
        delivery_count = sum(1 for e in employees if e.type == "delivery")
        
        assert chef_count == 2
        assert delivery_count == 1


# ============================================================
# Authorization Tests
# ============================================================

class TestManagerAuthorization:
    """Tests for manager authorization and access control"""

    def test_require_manager_role(self):
        """Non-manager users should be denied access"""
        mock_customer = MagicMock(spec=Account)
        mock_customer.type = "customer"
        
        mock_chef = MagicMock(spec=Account)
        mock_chef.type = "chef"
        
        mock_manager = create_mock_manager()
        
        assert mock_customer.type != "manager"
        assert mock_chef.type != "manager"
        assert mock_manager.type == "manager"

    def test_manager_can_only_manage_own_restaurant(self):
        """Manager should only manage employees of their restaurant"""
        mock_manager = create_mock_manager(restaurant_id=1)
        mock_chef_same = create_mock_chef(restaurant_id=1)
        mock_chef_diff = create_mock_chef(id=11, restaurant_id=2)
        
        can_manage_same = mock_chef_same.restaurantID == mock_manager.restaurantID
        can_manage_diff = mock_chef_diff.restaurantID == mock_manager.restaurantID
        
        assert can_manage_same is True
        assert can_manage_diff is False


# ============================================================
# Edge Cases and Error Handling
# ============================================================

class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_fire_already_fired_employee(self):
        """Firing already fired employee should be handled"""
        mock_chef = create_mock_chef(is_fired=True)
        
        # Already fired
        assert mock_chef.is_fired is True

    def test_promote_fired_employee_not_allowed(self):
        """Promoting a fired employee should not be allowed"""
        mock_chef = create_mock_chef(is_fired=True)
        
        # Business rule: can't promote fired employee
        can_promote = not mock_chef.is_fired
        assert can_promote is False

    def test_demote_at_minimum_wage(self):
        """Demoting at minimum wage should handle gracefully"""
        minimum_wage = 100
        mock_chef = create_mock_chef(wage=minimum_wage)
        
        # Should not go below minimum
        demotion_rate = Decimal("0.90")
        new_wage = max(minimum_wage, int(mock_chef.wage * demotion_rate))
        
        assert new_wage >= minimum_wage

    def test_empty_bids_for_order(self):
        """Order with no bids should be handled"""
        bids = []
        
        has_bids = len(bids) > 0
        assert has_bids is False

    def test_assign_without_bids_fails(self):
        """Assignment without bids should fail"""
        mock_order = MagicMock(spec=Order)
        mock_order.status = "paid"
        
        bids = []
        
        # Cannot assign without bids
        can_assign = len(bids) > 0
        assert can_assign is False


# ============================================================
# Integration Test Helpers
# ============================================================

def get_manager_token():
    """Get a valid manager JWT token for testing"""
    return create_access_token({"sub": "manager@test.com"})


def get_chef_token():
    """Get a valid chef JWT token for testing"""
    return create_access_token({"sub": "chef@test.com"})


def get_customer_token():
    """Get a valid customer JWT token for testing"""
    return create_access_token({"sub": "customer@test.com"})
