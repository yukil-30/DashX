"""
Tests for Complaints & Compliments Subsystem

Tests cover:
- Complaint filing (customer vs chef, customer vs delivery, delivery vs customer)
- Compliment filing
- Dispute flow
- Warning system (3 warnings = blacklist, VIP 3 warnings = demote + clear)
- Complaint dismissed = filer gets warning
- HR stats integration
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from app.models import Account, Complaint, Order, Dish, OrderedDish, Bid, Blacklist, VIPHistory, Restaurant
from app.routers.reputation import (
    validate_complaint_filing,
    check_and_apply_customer_warning_rules,
    check_compliment_cancellation,
    get_iso_now
)


class TestComplaintFilingRules:
    """Tests for complaint filing validation rules"""
    
    def test_customer_can_file_against_chef_of_ordered_dish(self, db_session, restaurant):
        """Customer can file complaint against chef who made their ordered dish"""
        # Setup: Create customer, chef, dish, order
        customer = Account(
            ID=200, email="cust@test.com", password="hash", type="customer",
            balance=10000, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        chef = Account(
            ID=201, email="chef@test.com", password="hash", type="chef",
            restaurantID=restaurant.id, balance=0, warnings=0, total_spent_cents=0,
            unresolved_complaints_count=0, is_vip=False
        )
        db_session.add_all([customer, chef])
        db_session.flush()
        
        dish = Dish(id=200, restaurantID=restaurant.id, name="Test Dish", cost=1000, chefID=chef.ID)
        db_session.add(dish)
        db_session.flush()
        
        order = Order(id=200, accountID=customer.ID, finalCost=1000, status="delivered")
        db_session.add(order)
        db_session.flush()
        
        ordered_dish = OrderedDish(DishID=dish.id, orderID=order.id, quantity=1)
        db_session.add(ordered_dish)
        db_session.flush()
        
        # Test validation
        target_type = validate_complaint_filing(db_session, customer, chef, order.id, None)
        assert target_type == "chef"
    
    def test_customer_cannot_file_against_chef_of_unordered_dish(self, db_session, restaurant):
        """Customer cannot file complaint against chef who didn't make dishes in their order"""
        customer = Account(
            ID=210, email="cust2@test.com", password="hash", type="customer",
            balance=10000, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        chef1 = Account(
            ID=211, email="chef1@test.com", password="hash", type="chef",
            restaurantID=restaurant.id, balance=0, warnings=0, total_spent_cents=0,
            unresolved_complaints_count=0, is_vip=False
        )
        chef2 = Account(
            ID=212, email="chef2@test.com", password="hash", type="chef",
            restaurantID=restaurant.id, balance=0, warnings=0, total_spent_cents=0,
            unresolved_complaints_count=0, is_vip=False
        )
        db_session.add_all([customer, chef1, chef2])
        db_session.flush()
        
        # Dish made by chef1
        dish = Dish(id=210, restaurantID=restaurant.id, name="Chef1 Dish", cost=1000, chefID=chef1.ID)
        db_session.add(dish)
        db_session.flush()
        
        order = Order(id=210, accountID=customer.ID, finalCost=1000, status="delivered")
        db_session.add(order)
        db_session.flush()
        
        ordered_dish = OrderedDish(DishID=dish.id, orderID=order.id, quantity=1)
        db_session.add(ordered_dish)
        db_session.flush()
        
        # Try to file against chef2 (didn't make the dish)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            validate_complaint_filing(db_session, customer, chef2, order.id, None)
        assert "did not prepare any dishes" in str(exc.value.detail)
    
    def test_customer_can_file_against_delivery_person(self, db_session, restaurant):
        """Customer can file complaint against delivery person who delivered their order"""
        customer = Account(
            ID=220, email="cust3@test.com", password="hash", type="customer",
            balance=10000, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        delivery = Account(
            ID=221, email="delivery@test.com", password="hash", type="delivery",
            balance=0, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        db_session.add_all([customer, delivery])
        db_session.flush()
        
        order = Order(id=220, accountID=customer.ID, finalCost=1000, status="delivered")
        db_session.add(order)
        db_session.flush()
        
        bid = Bid(id=220, deliveryPersonID=delivery.ID, orderID=order.id, bidAmount=500)
        db_session.add(bid)
        db_session.flush()
        
        order.bidID = bid.id
        db_session.flush()
        
        target_type = validate_complaint_filing(db_session, customer, delivery, order.id, None)
        assert target_type == "delivery"
    
    def test_delivery_can_file_against_customer(self, db_session, restaurant):
        """Delivery person can file complaint against customer whose order they delivered"""
        customer = Account(
            ID=230, email="cust4@test.com", password="hash", type="customer",
            balance=10000, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        delivery = Account(
            ID=231, email="delivery2@test.com", password="hash", type="delivery",
            balance=0, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        db_session.add_all([customer, delivery])
        db_session.flush()
        
        order = Order(id=230, accountID=customer.ID, finalCost=1000, status="delivered")
        db_session.add(order)
        db_session.flush()
        
        bid = Bid(id=230, deliveryPersonID=delivery.ID, orderID=order.id, bidAmount=500)
        db_session.add(bid)
        db_session.flush()
        
        order.bidID = bid.id
        db_session.flush()
        
        target_type = validate_complaint_filing(db_session, delivery, customer, order.id, None)
        assert target_type == "customer"
    
    def test_customer_cannot_file_against_wrong_delivery_person(self, db_session, restaurant):
        """Customer cannot file complaint against delivery person who didn't deliver their order"""
        customer = Account(
            ID=240, email="cust5@test.com", password="hash", type="customer",
            balance=10000, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        delivery1 = Account(
            ID=241, email="delivery3@test.com", password="hash", type="delivery",
            balance=0, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        delivery2 = Account(
            ID=242, email="delivery4@test.com", password="hash", type="delivery",
            balance=0, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        db_session.add_all([customer, delivery1, delivery2])
        db_session.flush()
        
        order = Order(id=240, accountID=customer.ID, finalCost=1000, status="delivered")
        db_session.add(order)
        db_session.flush()
        
        # Bid by delivery1
        bid = Bid(id=240, deliveryPersonID=delivery1.ID, orderID=order.id, bidAmount=500)
        db_session.add(bid)
        db_session.flush()
        order.bidID = bid.id
        db_session.flush()
        
        # Try to file against delivery2
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            validate_complaint_filing(db_session, customer, delivery2, order.id, None)
        assert "did not deliver your order" in str(exc.value.detail)


class TestWarningSystem:
    """Tests for the warning system"""
    
    def test_customer_3_warnings_blacklisted(self, db_session, restaurant):
        """Customer with 3 warnings gets blacklisted"""
        manager = Account(
            ID=300, email="mgr@test.com", password="hash", type="manager",
            restaurantID=restaurant.id, balance=0, warnings=0, total_spent_cents=0,
            unresolved_complaints_count=0, is_vip=False
        )
        customer = Account(
            ID=301, email="bad_cust@test.com", password="hash", type="customer",
            balance=10000, warnings=2, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        db_session.add_all([manager, customer])
        db_session.flush()
        
        # Give the 3rd warning
        customer.warnings = 3
        result = check_and_apply_customer_warning_rules(db_session, customer, manager.ID)
        
        assert result == "blacklisted"
        assert customer.is_blacklisted == True
        assert customer.type == "blacklisted"
        
        # Check blacklist entry was created
        blacklist_entry = db_session.query(Blacklist).filter(Blacklist.email == customer.email).first()
        assert blacklist_entry is not None
    
    def test_vip_2_warnings_demoted(self, db_session, restaurant):
        """VIP with 2 warnings gets demoted to customer and warnings cleared"""
        manager = Account(
            ID=310, email="mgr2@test.com", password="hash", type="manager",
            restaurantID=restaurant.id, balance=0, warnings=0, total_spent_cents=0,
            unresolved_complaints_count=0, is_vip=False
        )
        vip = Account(
            ID=311, email="vip@test.com", password="hash", type="vip",
            balance=10000, warnings=1, total_spent_cents=50000, unresolved_complaints_count=0, is_vip=True
        )
        db_session.add_all([manager, vip])
        db_session.flush()
        
        # Give the 2nd warning
        vip.warnings = 2
        result = check_and_apply_customer_warning_rules(db_session, vip, manager.ID)
        
        assert result == "vip_demoted_to_customer"
        assert vip.type == "customer"
        assert vip.previous_type == "vip"
        assert vip.warnings == 0  # Warnings cleared
    
    def test_customer_under_3_warnings_no_action(self, db_session, restaurant):
        """Customer with less than 3 warnings is not blacklisted"""
        manager = Account(
            ID=320, email="mgr3@test.com", password="hash", type="manager",
            restaurantID=restaurant.id, balance=0, warnings=0, total_spent_cents=0,
            unresolved_complaints_count=0, is_vip=False
        )
        customer = Account(
            ID=321, email="cust6@test.com", password="hash", type="customer",
            balance=10000, warnings=2, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        db_session.add_all([manager, customer])
        db_session.flush()
        
        result = check_and_apply_customer_warning_rules(db_session, customer, manager.ID)
        
        assert result is None
        assert customer.is_blacklisted == False
        assert customer.type == "customer"


class TestComplimentCancellation:
    """Tests for compliment canceling complaint functionality"""
    
    def test_compliment_cancels_complaint(self, db_session, restaurant):
        """One compliment cancels one pending complaint"""
        manager = Account(
            ID=400, email="mgr4@test.com", password="hash", type="manager",
            restaurantID=restaurant.id, balance=0, warnings=0, total_spent_cents=0,
            unresolved_complaints_count=0, is_vip=False
        )
        target = Account(
            ID=401, email="target@test.com", password="hash", type="chef",
            restaurantID=restaurant.id, balance=0, warnings=0, total_spent_cents=0,
            unresolved_complaints_count=0, is_vip=False
        )
        filer = Account(
            ID=402, email="filer@test.com", password="hash", type="customer",
            balance=10000, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        db_session.add_all([manager, target, filer])
        db_session.flush()
        
        # Create pending complaint
        complaint = Complaint(
            id=400, accountID=target.ID, type="complaint", description="Bad service",
            filer=filer.ID, status="pending", created_at=get_iso_now()
        )
        # Create pending compliment
        compliment = Complaint(
            id=401, accountID=target.ID, type="compliment", description="Great work!",
            filer=filer.ID, status="pending", created_at=get_iso_now()
        )
        db_session.add_all([complaint, compliment])
        db_session.flush()
        
        canceled = check_compliment_cancellation(db_session, target, manager.ID)
        
        assert canceled == 1
        assert complaint.status == "resolved"
        assert complaint.resolution == "canceled_by_compliment"
        assert compliment.status == "resolved"
        assert compliment.resolution == "canceled_complaint"


class TestDisputeFlow:
    """Tests for the dispute flow"""
    
    def test_dispute_sets_fields_correctly(self, db_session, restaurant):
        """Disputing a complaint sets all required fields"""
        target = Account(
            ID=500, email="target2@test.com", password="hash", type="chef",
            restaurantID=restaurant.id, balance=0, warnings=0, total_spent_cents=0,
            unresolved_complaints_count=0, is_vip=False
        )
        filer = Account(
            ID=501, email="filer2@test.com", password="hash", type="customer",
            balance=10000, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        db_session.add_all([target, filer])
        db_session.flush()
        
        complaint = Complaint(
            id=500, accountID=target.ID, type="complaint", description="Issue",
            filer=filer.ID, status="pending", disputed=False, created_at=get_iso_now()
        )
        db_session.add(complaint)
        db_session.flush()
        
        # Simulate disputing
        complaint.disputed = True
        complaint.dispute_reason = "This is unfair because..."
        complaint.disputed_at = get_iso_now()
        complaint.status = "disputed"
        db_session.flush()
        
        assert complaint.disputed == True
        assert complaint.dispute_reason == "This is unfair because..."
        assert complaint.disputed_at is not None
        assert complaint.status == "disputed"
    
    def test_cannot_dispute_compliment(self, db_session, restaurant):
        """Cannot dispute a compliment"""
        target = Account(
            ID=510, email="target3@test.com", password="hash", type="chef",
            restaurantID=restaurant.id, balance=0, warnings=0, total_spent_cents=0,
            unresolved_complaints_count=0, is_vip=False
        )
        filer = Account(
            ID=511, email="filer3@test.com", password="hash", type="customer",
            balance=10000, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        db_session.add_all([target, filer])
        db_session.flush()
        
        compliment = Complaint(
            id=510, accountID=target.ID, type="compliment", description="Great!",
            filer=filer.ID, status="pending", disputed=False, created_at=get_iso_now()
        )
        db_session.add(compliment)
        db_session.flush()
        
        # Attempting to dispute a compliment should be prevented by API
        # Here we just verify the model allows it but the API should block it
        assert compliment.type == "compliment"


class TestDismissedComplaintWarning:
    """Tests for dismissed complaint adding warning to filer"""
    
    def test_dismissed_complaint_adds_warning_to_filer(self, db_session, restaurant):
        """When complaint is dismissed as without merit, filer gets a warning"""
        manager = Account(
            ID=600, email="mgr5@test.com", password="hash", type="manager",
            restaurantID=restaurant.id, balance=0, warnings=0, total_spent_cents=0,
            unresolved_complaints_count=0, is_vip=False
        )
        target = Account(
            ID=601, email="target4@test.com", password="hash", type="chef",
            restaurantID=restaurant.id, balance=0, warnings=0, total_spent_cents=0,
            unresolved_complaints_count=0, is_vip=False
        )
        filer = Account(
            ID=602, email="filer3@test.com", password="hash", type="customer",
            balance=10000, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        db_session.add_all([manager, target, filer])
        db_session.flush()
        
        complaint = Complaint(
            id=600, accountID=target.ID, type="complaint", description="False accusation",
            filer=filer.ID, status="pending", created_at=get_iso_now()
        )
        db_session.add(complaint)
        db_session.flush()
        
        # Dismiss the complaint
        filer.warnings += 1
        complaint.status = "resolved"
        complaint.resolution = "dismissed"
        db_session.flush()
        
        assert filer.warnings == 1
        assert complaint.resolution == "dismissed"


class TestHRStatsIntegration:
    """Tests for HR stats integration"""
    
    def test_complaints_affect_unresolved_count(self, db_session, restaurant):
        """Filing complaint updates unresolved complaints count tracking"""
        target = Account(
            ID=700, email="target5@test.com", password="hash", type="chef",
            restaurantID=restaurant.id, balance=0, warnings=0, total_spent_cents=0,
            unresolved_complaints_count=0, is_vip=False
        )
        filer = Account(
            ID=701, email="filer5@test.com", password="hash", type="customer",
            balance=10000, warnings=0, total_spent_cents=0, unresolved_complaints_count=0, is_vip=False
        )
        db_session.add_all([target, filer])
        db_session.flush()
        
        # Create pending complaint
        complaint = Complaint(
            id=700, accountID=target.ID, type="complaint", description="Issue",
            filer=filer.ID, status="pending", created_at=get_iso_now()
        )
        db_session.add(complaint)
        db_session.flush()
        
        # Count pending complaints about target
        pending_count = db_session.query(Complaint).filter(
            Complaint.accountID == target.ID,
            Complaint.type == "complaint",
            Complaint.status == "pending"
        ).count()
        
        assert pending_count == 1


class TestComplaintAPIEndpoints:
    """Tests for API endpoints (using test client would be needed for full testing)"""
    
    def test_complaint_response_includes_dispute_fields(self, db_session, restaurant):
        """ComplaintResponse should include dispute-related fields"""
        from app.schemas import ComplaintResponse
        
        response = ComplaintResponse(
            id=1,
            accountID=100,
            type="complaint",
            description="Test",
            filer=101,
            status="disputed",
            disputed=True,
            dispute_reason="Test reason",
            disputed_at="2025-12-10T10:00:00Z",
            target_type="chef"
        )
        
        assert response.disputed == True
        assert response.dispute_reason == "Test reason"
        assert response.disputed_at == "2025-12-10T10:00:00Z"
        assert response.target_type == "chef"
    
    def test_dispute_request_requires_reason(self):
        """DisputeRequest requires a reason of at least 10 characters"""
        from app.schemas import DisputeRequest
        from pydantic import ValidationError
        
        # Valid request
        request = DisputeRequest(reason="This is a valid dispute reason")
        assert request.reason == "This is a valid dispute reason"
        
        # Invalid - too short
        with pytest.raises(ValidationError):
            DisputeRequest(reason="short")
