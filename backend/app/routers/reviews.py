"""
Reviews Router
Handles dish reviews and delivery reviews for completed orders.
UPDATED: Allow reviews on 'paid' orders for testing/development
Integrates with reputation engine for automatic rule evaluation.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import get_current_user
from app.models import (
    Account, Dish, Order, OrderedDish, DishReview, OrderDeliveryReview,
    DeliveryRating, Bid
)
from app.schemas import (
    DishReviewCreateRequest, DishReviewResponse, DishReviewListResponse,
    DeliveryReviewCreateRequest, DeliveryReviewResponse
)
from app import reputation_engine as rep_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("/dish", response_model=DishReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_dish_review(
    request: DishReviewCreateRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Create a review for a dish from a completed order.
    
    UPDATED: Allow reviews on 'paid' orders (not just delivered)
    - User must have ordered this dish
    - Order must be paid or delivered
    - Can only review once per dish per order
    """
    # Verify order exists and belongs to user
    order = db.query(Order).filter(
        Order.id == request.order_id,
        Order.accountID == current_user.ID
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # UPDATED: Allow reviews for 'paid' orders (not just delivered)
    if order.status not in ['paid', 'assigned', 'in_transit', 'delivered']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only review dishes from paid or delivered orders"
        )
    
    # Verify dish was in the order
    ordered_dish = db.query(OrderedDish).filter(
        OrderedDish.orderID == request.order_id,
        OrderedDish.DishID == request.dish_id
    ).first()
    
    if not ordered_dish:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This dish was not part of the order"
        )
    
    # Check for existing review
    existing = db.query(DishReview).filter(
        DishReview.dish_id == request.dish_id,
        DishReview.account_id == current_user.ID,
        DishReview.order_id == request.order_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this dish for this order"
        )
    
    # Get dish
    dish = db.query(Dish).filter(Dish.id == request.dish_id).first()
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create review
    review = DishReview(
        dish_id=request.dish_id,
        account_id=current_user.ID,
        order_id=request.order_id,
        rating=request.rating,
        review_text=request.review_text,
        created_at=now
    )
    db.add(review)
    
    # Update dish average rating
    # Get all reviews for this dish
    all_reviews = db.query(DishReview).filter(
        DishReview.dish_id == request.dish_id
    ).all()
    
    total_rating = sum(r.rating for r in all_reviews) + request.rating
    new_count = len(all_reviews) + 1
    new_average = Decimal(str(total_rating / new_count))
    
    dish.average_rating = round(new_average, 2)
    dish.reviews = new_count
    
    # Trigger reputation engine for chef rating update
    rule_results = None
    if dish.chefID:
        chef = db.query(Account).filter(Account.ID == dish.chefID).first()
        if chef:
            # Recalculate chef's rolling average from all their dishes
            rep_engine.recalculate_chef_rating_from_dishes(db, chef)
            
            # Evaluate rules (may trigger demotion/bonus)
            rule_results = rep_engine.evaluate_employee_rules(db, chef, current_user.ID)
    
    db.commit()
    db.refresh(review)
    
    logger.info(f"Dish review created: dish={request.dish_id}, user={current_user.ID}, rating={request.rating}")
    
    return DishReviewResponse(
        id=review.id,
        dish_id=review.dish_id,
        dish_name=dish.name,
        account_id=review.account_id,
        reviewer_email=current_user.email,
        order_id=review.order_id,
        rating=review.rating,
        review_text=review.review_text,
        created_at=review.created_at
    )


@router.get("/dish/{dish_id}", response_model=DishReviewListResponse)
async def get_dish_reviews(
    dish_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get all reviews for a specific dish.
    """
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        )
    
    query = db.query(DishReview).filter(
        DishReview.dish_id == dish_id
    ).options(joinedload(DishReview.account))
    
    total = query.count()
    offset = (page - 1) * per_page
    
    reviews = query.order_by(desc(DishReview.id)).offset(offset).limit(per_page).all()
    
    avg_rating = db.query(func.avg(DishReview.rating)).filter(
        DishReview.dish_id == dish_id
    ).scalar() or 0.0
    
    return DishReviewListResponse(
        reviews=[
            DishReviewResponse(
                id=r.id,
                dish_id=r.dish_id,
                dish_name=dish.name,
                account_id=r.account_id,
                reviewer_email=r.account.email if r.account else None,
                order_id=r.order_id,
                rating=r.rating,
                review_text=r.review_text,
                created_at=r.created_at
            )
            for r in reviews
        ],
        total=total,
        average_rating=float(avg_rating)
    )


@router.post("/delivery", response_model=DeliveryReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_review(
    request: DeliveryReviewCreateRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Create a review for delivery on a completed order.
    
    UPDATED: Allow delivery reviews on assigned/in_transit orders for testing
    - Order must be assigned, in_transit, or delivered
    - Order must have an assigned delivery person
    - Can only review once per order
    """
    # Verify order exists and belongs to user
    order = db.query(Order).filter(
        Order.id == request.order_id,
        Order.accountID == current_user.ID
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # UPDATED: Allow reviews for assigned/in_transit orders too
    if order.status not in ['assigned', 'in_transit', 'delivered']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only review delivery for orders with assigned delivery"
        )
    
    if not order.bidID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order does not have an assigned delivery"
        )
    
    # Get delivery person from accepted bid
    bid = db.query(Bid).filter(Bid.id == order.bidID).first()
    if not bid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery bid not found"
        )
    
    # Check for existing review
    existing = db.query(OrderDeliveryReview).filter(
        OrderDeliveryReview.order_id == request.order_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed the delivery for this order"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create review
    review = OrderDeliveryReview(
        order_id=request.order_id,
        delivery_person_id=bid.deliveryPersonID,
        reviewer_id=current_user.ID,
        rating=request.rating,
        review_text=request.review_text,
        on_time=request.on_time,
        created_at=now
    )
    db.add(review)
    
    # Update delivery person's overall rating
    delivery_rating = db.query(DeliveryRating).filter(
        DeliveryRating.accountID == bid.deliveryPersonID
    ).first()
    
    if not delivery_rating:
        delivery_rating = DeliveryRating(
            accountID=bid.deliveryPersonID,
            averageRating=Decimal("0.00"),
            reviews=0,
            total_deliveries=0,
            on_time_deliveries=0
        )
        db.add(delivery_rating)
    
    # Update stats
    total_rating = float(delivery_rating.averageRating or 0) * delivery_rating.reviews
    total_rating += request.rating
    delivery_rating.reviews += 1
    delivery_rating.averageRating = Decimal(str(total_rating / delivery_rating.reviews))
    delivery_rating.total_deliveries += 1
    
    if request.on_time:
        delivery_rating.on_time_deliveries += 1
    
    # Trigger reputation engine for delivery person rating update
    rule_results = None
    delivery_person = db.query(Account).filter(Account.ID == bid.deliveryPersonID).first()
    if delivery_person:
        # Update the rolling average on the account as well
        rep_engine.update_employee_rating(db, delivery_person, request.rating, current_user.ID)
        # Sync from DeliveryRating table
        rep_engine.recalculate_delivery_rating(db, delivery_person)
        # Evaluate rules
        rule_results = rep_engine.evaluate_employee_rules(db, delivery_person, current_user.ID)
    
    db.commit()
    db.refresh(review)
    
    logger.info(f"Delivery review created: order={request.order_id}, delivery_person={bid.deliveryPersonID}, rating={request.rating}")
    
    return DeliveryReviewResponse(
        id=review.id,
        order_id=review.order_id,
        delivery_person_id=review.delivery_person_id,
        delivery_person_email=delivery_person.email if delivery_person else None,
        reviewer_id=review.reviewer_id,
        rating=review.rating,
        review_text=review.review_text,
        on_time=review.on_time,
        created_at=review.created_at
    )


@router.get("/my-reviews")
async def get_my_reviews(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Get all reviews created by the current user.
    """
    dish_reviews = db.query(DishReview).filter(
        DishReview.account_id == current_user.ID
    ).options(joinedload(DishReview.dish)).order_by(desc(DishReview.id)).all()
    
    delivery_reviews = db.query(OrderDeliveryReview).filter(
        OrderDeliveryReview.reviewer_id == current_user.ID
    ).order_by(desc(OrderDeliveryReview.id)).all()
    
    return {
        "dish_reviews": [
            DishReviewResponse(
                id=r.id,
                dish_id=r.dish_id,
                dish_name=r.dish.name if r.dish else "Unknown",
                account_id=r.account_id,
                order_id=r.order_id,
                rating=r.rating,
                review_text=r.review_text,
                created_at=r.created_at
            )
            for r in dish_reviews
        ],
        "delivery_reviews": [
            DeliveryReviewResponse(
                id=r.id,
                order_id=r.order_id,
                delivery_person_id=r.delivery_person_id,
                reviewer_id=r.reviewer_id,
                rating=r.rating,
                review_text=r.review_text,
                on_time=r.on_time,
                created_at=r.created_at
            )
            for r in delivery_reviews
        ],
        "total_dish_reviews": len(dish_reviews),
        "total_delivery_reviews": len(delivery_reviews)
    }