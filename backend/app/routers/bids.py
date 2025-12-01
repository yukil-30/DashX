"""
Bids Router - Handles delivery bidding
POST /bids - Create a new bid (with order_id in body)
GET /bids/scoreboard - Get delivery person scoreboard
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc

from app.database import get_db
from app.auth import get_current_user, require_manager
from app.models import Account, Order, Bid, DeliveryRating
from app.schemas import (
    BidCreateRequest,
    BidResponse,
    DeliveryPersonStats,
)

router = APIRouter(prefix="/bids", tags=["Bids"])


@router.post("", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def create_bid_standalone(
    bid_request: BidCreateRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Submit a delivery bid for an order.
    This is an alternative to POST /orders/{id}/bid that takes order_id in the body.
    Only delivery personnel can submit bids.
    Order must be in 'paid' status (open for bidding).
    """
    # Only delivery personnel can bid
    if current_user.type != "delivery":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only delivery personnel can submit bids"
        )
    
    # Validate order_id is provided
    if bid_request.order_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="order_id is required"
        )
    
    order_id = bid_request.order_id
    
    # Get order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )
    
    # Order must be in 'paid' status for bidding
    if order.status != "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order is not open for bidding. Current status: {order.status}"
        )
    
    # Check if this delivery person already bid on this order
    existing_bid = db.query(Bid).filter(
        Bid.orderID == order_id,
        Bid.deliveryPersonID == current_user.ID
    ).first()
    
    if existing_bid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted a bid for this order"
        )
    
    # Create bid
    bid = Bid(
        deliveryPersonID=current_user.ID,
        orderID=order_id,
        bidAmount=bid_request.price_cents,
        estimated_minutes=bid_request.estimated_minutes
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)
    
    # Check if this is the lowest bid
    lowest_bid = db.query(Bid).filter(
        Bid.orderID == order_id
    ).order_by(Bid.bidAmount.asc()).first()
    
    is_lowest = lowest_bid is not None and lowest_bid.id == bid.id
    
    return BidResponse(
        id=bid.id,
        deliveryPersonID=bid.deliveryPersonID,
        orderID=bid.orderID,
        bidAmount=bid.bidAmount,
        estimated_minutes=bid.estimated_minutes,
        delivery_person_email=current_user.email,
        is_lowest=is_lowest
    )


@router.get("/scoreboard", response_model=List[DeliveryPersonStats])
async def get_delivery_scoreboard(
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    sort_by: str = Query("rating", description="Sort by: rating, on_time, deliveries"),
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_manager)
):
    """
    Get a scoreboard of all delivery personnel with their stats.
    Manager-only endpoint for evaluating delivery people.
    """
    # Get all delivery personnel with their ratings
    delivery_accounts = db.query(Account).filter(
        Account.type == "delivery"
    ).all()
    
    results = []
    for account in delivery_accounts:
        # Get delivery rating
        rating = db.query(DeliveryRating).filter(
            DeliveryRating.accountID == account.ID
        ).first()
        
        on_time_pct = 0.0
        if rating and rating.total_deliveries > 0:
            on_time_pct = (rating.on_time_deliveries / rating.total_deliveries) * 100
        
        results.append(DeliveryPersonStats(
            account_id=account.ID,
            email=account.email,
            average_rating=float(rating.averageRating) if rating else 0.0,
            reviews=rating.reviews if rating else 0,
            total_deliveries=rating.total_deliveries if rating else 0,
            on_time_deliveries=rating.on_time_deliveries if rating else 0,
            on_time_percentage=round(on_time_pct, 1),
            avg_delivery_minutes=rating.avg_delivery_minutes if rating else 30,
            warnings=account.warnings
        ))
    
    # Sort results
    if sort_by == "rating":
        results.sort(key=lambda x: (-x.average_rating, -x.reviews))
    elif sort_by == "on_time":
        results.sort(key=lambda x: (-x.on_time_percentage, -x.total_deliveries))
    elif sort_by == "deliveries":
        results.sort(key=lambda x: (-x.total_deliveries, -x.average_rating))
    else:
        results.sort(key=lambda x: (-x.average_rating, -x.reviews))
    
    return results[:limit]
