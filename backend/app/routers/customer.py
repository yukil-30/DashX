"""
Customer Dashboard Router
Provides customer-facing dashboard data including:
- VIP status and benefits
- Balance information
- Recent orders
- Favorite dishes
- Popular/highest-rated dishes
- Top rated chef
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import get_current_user
from app.models import (
    Account, Dish, Order, OrderedDish, Complaint, 
    DishReview, DeliveryRating, AccountProfile, VIPHistory
)
from app.schemas import (
    CustomerDashboardResponse, VIPStatus, OrderSummary, 
    ChefProfileSummary, DishResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customer", tags=["Customer Dashboard"])

# VIP Configuration
VIP_SPEND_THRESHOLD_CENTS = 10000  # $100 to become VIP
VIP_ORDERS_THRESHOLD = 3  # Or 3 orders
VIP_DISCOUNT_PERCENT = 5  # 5% discount for VIP
VIP_FREE_DELIVERY_EVERY_N_ORDERS = 3  # Free delivery every 3 orders


def format_cents_to_dollars(cents: int) -> str:
    """Format cents as dollar string"""
    dollars = cents / 100
    return f"${dollars:,.2f}"


def dish_to_response(dish: Dish) -> DishResponse:
    """Convert Dish model to DishResponse schema"""
    return DishResponse(
        id=dish.id,
        name=dish.name,
        description=dish.description,
        cost=dish.cost,
        cost_formatted=format_cents_to_dollars(dish.cost),
        picture=dish.picture,
        average_rating=float(dish.average_rating or 0),
        reviews=dish.reviews,
        chefID=dish.chefID,
        restaurantID=dish.restaurantID
    )


def check_vip_eligibility(db: Session, account: Account) -> VIPStatus:
    """
    Check if a customer is eligible for VIP status.
    
    VIP rules:
    - Spend > $100 OR complete 3 orders as registered customer
    - No unresolved complaints
    
    VIP benefits:
    - 5% discount on food price
    - 1 free delivery per every 3 orders
    """
    # Get unresolved complaints count
    unresolved_complaints = db.query(Complaint).filter(
        Complaint.filer == account.ID,
        Complaint.status == 'pending'
    ).count()
    
    has_unresolved = unresolved_complaints > 0
    
    # Get total spent from completed orders
    total_spent = db.query(func.sum(Order.finalCost)).filter(
        Order.accountID == account.ID,
        Order.status == 'delivered'
    ).scalar() or 0
    
    # Get completed orders count
    completed_orders = db.query(Order).filter(
        Order.accountID == account.ID,
        Order.status == 'delivered'
    ).count()
    
    # Check eligibility
    meets_spend_threshold = total_spent >= VIP_SPEND_THRESHOLD_CENTS
    meets_orders_threshold = completed_orders >= VIP_ORDERS_THRESHOLD
    vip_eligible = (meets_spend_threshold or meets_orders_threshold) and not has_unresolved
    
    is_vip = account.type == 'vip'
    
    # Calculate orders until next free delivery
    orders_since_last_credit = completed_orders % VIP_FREE_DELIVERY_EVERY_N_ORDERS
    next_free_delivery_in = VIP_FREE_DELIVERY_EVERY_N_ORDERS - orders_since_last_credit
    if next_free_delivery_in == VIP_FREE_DELIVERY_EVERY_N_ORDERS:
        next_free_delivery_in = 0  # Just earned one
    
    # Determine VIP reason
    if is_vip:
        if meets_spend_threshold:
            vip_reason = f"VIP: Spent over ${VIP_SPEND_THRESHOLD_CENTS/100:.0f}"
        else:
            vip_reason = f"VIP: Completed {VIP_ORDERS_THRESHOLD}+ orders"
    elif has_unresolved:
        vip_reason = "Not eligible: Has unresolved complaints"
    elif not meets_spend_threshold and not meets_orders_threshold:
        spend_needed = (VIP_SPEND_THRESHOLD_CENTS - total_spent) / 100
        orders_needed = VIP_ORDERS_THRESHOLD - completed_orders
        vip_reason = f"Spend ${spend_needed:.2f} more or complete {orders_needed} more orders"
    else:
        vip_reason = "Eligible for VIP upgrade"
    
    return VIPStatus(
        is_vip=is_vip,
        total_spent_cents=total_spent,
        total_spent_formatted=format_cents_to_dollars(total_spent),
        completed_orders=completed_orders,
        has_unresolved_complaints=has_unresolved,
        vip_eligible=vip_eligible,
        vip_reason=vip_reason,
        free_delivery_credits=account.free_delivery_credits,
        discount_percent=VIP_DISCOUNT_PERCENT if is_vip else 0,
        next_free_delivery_in=next_free_delivery_in if is_vip else 0
    )


def upgrade_to_vip_if_eligible(db: Session, account: Account) -> bool:
    """
    Check and upgrade customer to VIP if eligible.
    Returns True if upgraded.
    """
    if account.type == 'vip':
        return False
    
    # ✅ FIXED: Only allow customers to be upgraded
    if account.type not in ['customer']:
        return False
    
    # ✅ FIXED: Don't re-promote customers who were demoted from VIP
    if account.previous_type == 'vip':
        return False
    
    vip_status = check_vip_eligibility(db, account)
    
    if vip_status.vip_eligible:
        # Create VIP history entry
        vip_entry = VIPHistory(
            account_id=account.ID,
            previous_type=account.type,
            new_type='vip',
            reason=vip_status.vip_reason,
            changed_by=None,  # Automatic
            created_at=datetime.now(timezone.utc).isoformat()
        )
        db.add(vip_entry)
        
        # Update account
        account.previous_type = account.type
        account.type = 'vip'
        
        db.commit()
        logger.info(f"Account {account.ID} upgraded to VIP: {vip_status.vip_reason}")
        return True
    
    return False


@router.get("/dashboard", response_model=CustomerDashboardResponse)
async def get_customer_dashboard(
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Get customer dashboard data including:
    - VIP status and benefits
    - Balance
    - Recent orders
    - Favorite dishes
    - Most popular dish
    - Highest rated dish
    - Top rated chef
    
    ✅ Accessible by both 'customer' and 'vip' account types
    """
    # ✅ FIXED: Check if user is customer or VIP
    if current_user.type not in ['customer', 'vip']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Customer or VIP account required."
        )
    
    # Check VIP eligibility and upgrade if needed (only for customers)
    upgrade_to_vip_if_eligible(db, current_user)
    db.refresh(current_user)
    
    # Get VIP status
    vip_status = check_vip_eligibility(db, current_user)
    
    # Get recent orders (last 5)
    recent_orders_query = db.query(Order).filter(
        Order.accountID == current_user.ID
    ).order_by(desc(Order.id)).limit(5).all()
    
    recent_orders = [
        OrderSummary(
            id=order.id,
            status=order.status,
            total_cents=order.finalCost,
            total_formatted=format_cents_to_dollars(order.finalCost),
            items_count=len(order.ordered_dishes),
            created_at=order.dateTime or "",
            can_review=order.status == 'delivered'
        )
        for order in recent_orders_query
    ]
    
    # Get favorite dishes (most ordered by this user)
    favorite_dishes_subq = db.query(
        OrderedDish.DishID,
        func.sum(OrderedDish.quantity).label('total_qty')
    ).join(Order).filter(
        Order.accountID == current_user.ID
    ).group_by(OrderedDish.DishID).subquery()
    
    favorite_dishes_query = db.query(Dish).join(
        favorite_dishes_subq, Dish.id == favorite_dishes_subq.c.DishID
    ).order_by(desc(favorite_dishes_subq.c.total_qty)).limit(4).all()
    
    favorite_dishes = [dish_to_response(d) for d in favorite_dishes_query]
    
    # Get most popular dish globally
    most_popular = db.query(Dish).order_by(
        desc(Dish.reviews), desc(Dish.average_rating)
    ).first()
    
    # Get highest rated dish globally
    highest_rated = db.query(Dish).filter(
        Dish.reviews >= 1
    ).order_by(
        desc(Dish.average_rating), desc(Dish.reviews)
    ).first()
    
    # Get top rated chef
    top_chef_query = db.query(
        Account,
        func.avg(Dish.average_rating).label('avg_rating'),
        func.count(Dish.id).label('dish_count'),
        func.sum(Dish.reviews).label('total_reviews')
    ).join(Dish, Account.ID == Dish.chefID).filter(
        Account.type == 'chef'
    ).group_by(Account.ID).having(
        func.sum(Dish.reviews) >= 1
    ).order_by(
        desc('avg_rating'), desc('total_reviews')
    ).first()
    
    top_chef = None
    if top_chef_query:
        chef_account = top_chef_query[0]
        # Get chef profile if exists
        chef_profile = db.query(AccountProfile).filter(
            AccountProfile.account_id == chef_account.ID
        ).first()
        
        top_chef = ChefProfileSummary(
            id=chef_account.ID,
            email=chef_account.email,
            display_name=chef_profile.display_name if chef_profile else None,
            profile_picture=chef_profile.profile_picture if chef_profile else "/images/chef-placeholder.svg",
            specialty=chef_profile.specialty if chef_profile else None,
            average_rating=float(top_chef_query[1] or 0),
            total_dishes=top_chef_query[2] or 0,
            total_reviews=top_chef_query[3] or 0
        )
    
    return CustomerDashboardResponse(
        user_id=current_user.ID,
        email=current_user.email,
        account_type=current_user.type,
        balance_cents=current_user.balance,
        balance_formatted=format_cents_to_dollars(current_user.balance),
        vip_status=vip_status,
        recent_orders=recent_orders,
        favorite_dishes=favorite_dishes,
        most_popular_dish=dish_to_response(most_popular) if most_popular else None,
        highest_rated_dish=dish_to_response(highest_rated) if highest_rated else None,
        top_rated_chef=top_chef
    )


@router.post("/check-vip")
async def check_and_upgrade_vip(
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Manually check VIP eligibility and upgrade if eligible.
    """
    if current_user.type not in ['customer', 'vip']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only customers can check VIP status"
        )
    
    was_upgraded = upgrade_to_vip_if_eligible(db, current_user)
    db.refresh(current_user)
    vip_status = check_vip_eligibility(db, current_user)
    
    return {
        "upgraded": was_upgraded,
        "vip_status": vip_status,
        "message": "Congratulations! You are now a VIP!" if was_upgraded else vip_status.vip_reason
    }