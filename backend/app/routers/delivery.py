"""
Delivery Router - Handles delivery person workflows
GET /delivery/available-orders - Orders open for bidding
GET /delivery/my-bids - Current user's bids
GET /delivery/assigned - Orders assigned to this delivery person
POST /delivery/orders/{id}/mark-delivered - Mark order as delivered
GET /delivery/history - Delivery history with ratings
GET /delivery/stats - Delivery person's aggregate stats
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_

from app.database import get_db
from app.auth import get_current_user
from app.models import Account, Order, OrderedDish, Bid, DeliveryRating, OrderDeliveryReview
from app.schemas import BidCreateRequest, BidResponse

router = APIRouter(prefix="/delivery", tags=["Delivery"])

# Configuration
BIDDING_DURATION_MINUTES = 30  # How long bidding stays open
BID_THROTTLE_SECONDS = 30  # Minimum time between bids from same user


def require_delivery_person(current_user: Account = Depends(get_current_user)) -> Account:
    """Dependency to ensure user is a delivery person"""
    if current_user.type != "delivery":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only delivery personnel can access this endpoint"
        )
    return current_user


@router.get("/available-orders")
async def get_available_orders(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_delivery_person)
):
    """
    Get orders that are open for bidding.
    Only shows orders with status 'paid' and bidding not yet closed.
    """
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    
    # Get orders that are open for bidding
    query = db.query(Order).options(
        joinedload(Order.ordered_dishes).joinedload(OrderedDish.dish),
        joinedload(Order.account)
    ).filter(
        Order.status == "paid"
    )
    
    # Filter out orders where bidding has closed
    # Orders with bidding_closes_at set and past are excluded
    # Orders without bidding_closes_at are included (legacy or new orders)
    query = query.filter(
        (Order.bidding_closes_at == None) | 
        (Order.bidding_closes_at > now_str)
    )
    
    total = query.count()
    orders = query.order_by(Order.id.desc()).offset(offset).limit(limit).all()
    
    # Build response with bid info
    result = []
    for order in orders:
        # Check if current user has already bid
        user_bid = db.query(Bid).filter(
            Bid.orderID == order.id,
            Bid.deliveryPersonID == current_user.ID
        ).first()
        
        # Get bid count
        bid_count = db.query(Bid).filter(Bid.orderID == order.id).count()
        
        # Get lowest bid
        lowest_bid = db.query(Bid).filter(
            Bid.orderID == order.id
        ).order_by(Bid.bidAmount.asc()).first()
        
        # Build items list
        items = [
            {
                "dish_id": od.DishID,
                "dish_name": od.dish.name if od.dish else "Unknown",
                "quantity": od.quantity,
                "unit_price_cents": od.dish.cost if od.dish else 0
            }
            for od in order.ordered_dishes
        ]
        
        result.append({
            "id": order.id,
            "customer_email": order.account.email if order.account else "Unknown",
            "delivery_address": order.delivery_address,
            "subtotal_cents": order.subtotal_cents,
            "delivery_fee_cents": order.delivery_fee,
            "total_cents": order.finalCost,
            "created_at": order.dateTime,
            "bidding_closes_at": order.bidding_closes_at,
            "items": items,
            "items_count": sum(od.quantity for od in order.ordered_dishes),
            "bid_count": bid_count,
            "lowest_bid_cents": lowest_bid.bidAmount if lowest_bid else None,
            "has_user_bid": user_bid is not None,
            "user_bid_id": user_bid.id if user_bid else None,
            "user_bid_amount": user_bid.bidAmount if user_bid else None,
            "note": order.note
        })
    
    return {
        "orders": result,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/my-bids")
async def get_my_bids(
    status_filter: Optional[str] = Query(None, description="Filter: pending, accepted, rejected"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_delivery_person)
):
    """
    Get all bids placed by the current delivery person.
    """
    query = db.query(Bid).options(
        joinedload(Bid.order).joinedload(Order.ordered_dishes).joinedload(OrderedDish.dish)
    ).filter(
        Bid.deliveryPersonID == current_user.ID
    )
    
    total = query.count()
    bids = query.order_by(Bid.id.desc()).offset(offset).limit(limit).all()
    
    result = []
    for bid in bids:
        order = bid.order
        
        # Determine bid status
        bid_status = "pending"
        if order.status == "assigned" or order.status == "delivered":
            if order.bidID == bid.id:
                bid_status = "accepted"
            else:
                bid_status = "rejected"
        elif order.status not in ["paid"]:
            bid_status = "closed"
        
        # Apply status filter if provided
        if status_filter and bid_status != status_filter:
            continue
        
        # Check if lowest bid
        lowest_bid = db.query(Bid).filter(
            Bid.orderID == order.id
        ).order_by(Bid.bidAmount.asc()).first()
        
        result.append({
            "bid_id": bid.id,
            "order_id": order.id,
            "bid_amount_cents": bid.bidAmount,
            "estimated_minutes": bid.estimated_minutes,
            "created_at": bid.created_at,
            "bid_status": bid_status,
            "is_lowest": lowest_bid and lowest_bid.id == bid.id,
            "order_status": order.status,
            "order_delivery_address": order.delivery_address,
            "order_total_cents": order.finalCost
        })
    
    # Re-filter if status filter was applied
    if status_filter:
        total = len(result)
    
    return {
        "bids": result,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/orders/{order_id}/bid", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def place_bid(
    order_id: int,
    bid_request: BidCreateRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_delivery_person)
):
    """
    Place a bid on an order open for bidding.
    
    Enforces:
    - Order must be in 'paid' status
    - Bidding must not be closed
    - User cannot bid on same order twice
    - Bid throttle: minimum 30 seconds between bids
    """
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    
    # Get order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )
    
    # Order must be in 'paid' status
    if order.status != "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order is not open for bidding. Current status: {order.status}"
        )
    
    # Check if bidding has closed
    if order.bidding_closes_at:
        closes_at = datetime.fromisoformat(order.bidding_closes_at.replace('Z', '+00:00'))
        if now > closes_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bidding has closed for this order"
            )
    
    # Check if user already bid on this order
    existing_bid = db.query(Bid).filter(
        Bid.orderID == order_id,
        Bid.deliveryPersonID == current_user.ID
    ).first()
    
    if existing_bid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted a bid for this order"
        )
    
    # Check bid throttle - get user's most recent bid
    last_bid = db.query(Bid).filter(
        Bid.deliveryPersonID == current_user.ID
    ).order_by(Bid.id.desc()).first()
    
    if last_bid and last_bid.created_at:
        last_bid_time = datetime.fromisoformat(last_bid.created_at.replace('Z', '+00:00'))
        time_since_last_bid = (now - last_bid_time).total_seconds()
        if time_since_last_bid < BID_THROTTLE_SECONDS:
            wait_time = int(BID_THROTTLE_SECONDS - time_since_last_bid)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {wait_time} seconds before placing another bid"
            )
    
    # Create bid
    bid = Bid(
        deliveryPersonID=current_user.ID,
        orderID=order_id,
        bidAmount=bid_request.price_cents,
        estimated_minutes=bid_request.estimated_minutes,
        created_at=now_str
    )
    db.add(bid)
    
    # Set bidding close time if not already set
    if not order.bidding_closes_at:
        order.bidding_closes_at = (now + timedelta(minutes=BIDDING_DURATION_MINUTES)).isoformat()
    
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


@router.get("/assigned")
async def get_assigned_orders(
    status_filter: Optional[str] = Query(None, description="Filter: assigned, out_for_delivery"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_delivery_person)
):
    """
    Get orders assigned to this delivery person (bid was accepted).
    """
    # Get bids that were accepted (order.bidID points to this bid)
    accepted_bid_ids = db.query(Bid.id).filter(
        Bid.deliveryPersonID == current_user.ID
    ).subquery()
    
    query = db.query(Order).options(
        joinedload(Order.ordered_dishes).joinedload(OrderedDish.dish),
        joinedload(Order.account)
    ).filter(
        Order.bidID.in_(accepted_bid_ids),
        Order.status.in_(["assigned", "out_for_delivery", "preparing", "ready"])
    )
    
    if status_filter:
        query = query.filter(Order.status == status_filter)
    
    total = query.count()
    orders = query.order_by(Order.id.desc()).offset(offset).limit(limit).all()
    
    result = []
    for order in orders:
        # Get the accepted bid details
        accepted_bid = db.query(Bid).filter(Bid.id == order.bidID).first()
        
        items = [
            {
                "dish_id": od.DishID,
                "dish_name": od.dish.name if od.dish else "Unknown",
                "quantity": od.quantity
            }
            for od in order.ordered_dishes
        ]
        
        result.append({
            "id": order.id,
            "customer_email": order.account.email if order.account else "Unknown",
            "delivery_address": order.delivery_address,
            "total_cents": order.finalCost,
            "delivery_fee_cents": accepted_bid.bidAmount if accepted_bid else order.delivery_fee,
            "estimated_minutes": accepted_bid.estimated_minutes if accepted_bid else 30,
            "status": order.status,
            "created_at": order.dateTime,
            "items": items,
            "items_count": sum(od.quantity for od in order.ordered_dishes),
            "note": order.note
        })
    
    return {
        "orders": result,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/orders/{order_id}/mark-delivered")
async def mark_order_delivered(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_delivery_person)
):
    """
    Mark an assigned order as delivered.
    Only the assigned delivery person can mark as delivered.
    """
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    
    # Get order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )
    
    # Verify this delivery person is assigned
    if not order.bidID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order does not have an assigned delivery person"
        )
    
    assigned_bid = db.query(Bid).filter(Bid.id == order.bidID).first()
    if not assigned_bid or assigned_bid.deliveryPersonID != current_user.ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the assigned delivery person for this order"
        )
    
    # Check order can be marked delivered
    if order.status not in ["assigned", "out_for_delivery", "preparing", "ready"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order cannot be marked as delivered. Current status: {order.status}"
        )
    
    # Update order
    order.status = "delivered"
    order.delivered_at = now_str
    
    # Update delivery rating stats (increment total_deliveries)
    delivery_rating = db.query(DeliveryRating).filter(
        DeliveryRating.accountID == current_user.ID
    ).first()
    
    if not delivery_rating:
        from decimal import Decimal
        delivery_rating = DeliveryRating(
            accountID=current_user.ID,
            averageRating=Decimal("0.00"),
            reviews=0,
            total_deliveries=0,
            on_time_deliveries=0,
            avg_delivery_minutes=30
        )
        db.add(delivery_rating)
    
    delivery_rating.total_deliveries += 1
    
    # Check if on time (compare estimated to actual)
    if order.dateTime and assigned_bid.estimated_minutes:
        order_time = datetime.fromisoformat(order.dateTime.replace('Z', '+00:00'))
        expected_delivery = order_time + timedelta(minutes=assigned_bid.estimated_minutes)
        if now <= expected_delivery:
            delivery_rating.on_time_deliveries += 1
    
    db.commit()
    
    return {
        "message": "Order marked as delivered",
        "order_id": order_id,
        "delivered_at": now_str,
        "status": "delivered"
    }


@router.get("/history")
async def get_delivery_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_delivery_person)
):
    """
    Get delivery history with customer ratings and comments.
    Shows completed deliveries for this delivery person.
    """
    # Get accepted bids that are for delivered orders
    accepted_bid_ids = db.query(Bid.id).filter(
        Bid.deliveryPersonID == current_user.ID
    ).subquery()
    
    query = db.query(Order).options(
        joinedload(Order.ordered_dishes).joinedload(OrderedDish.dish),
        joinedload(Order.account)
    ).filter(
        Order.bidID.in_(accepted_bid_ids),
        Order.status == "delivered"
    )
    
    total = query.count()
    offset = (page - 1) * per_page
    orders = query.order_by(desc(Order.id)).offset(offset).limit(per_page).all()
    
    result = []
    for order in orders:
        # Get delivery review if any
        review = db.query(OrderDeliveryReview).filter(
            OrderDeliveryReview.order_id == order.id,
            OrderDeliveryReview.delivery_person_id == current_user.ID
        ).first()
        
        # Get accepted bid
        accepted_bid = db.query(Bid).filter(Bid.id == order.bidID).first()
        
        items = [
            {
                "dish_id": od.DishID,
                "dish_name": od.dish.name if od.dish else "Unknown",
                "quantity": od.quantity
            }
            for od in order.ordered_dishes
        ]
        
        result.append({
            "order_id": order.id,
            "customer_email": order.account.email if order.account else "Unknown",
            "delivery_address": order.delivery_address,
            "total_cents": order.finalCost,
            "delivery_fee_cents": accepted_bid.bidAmount if accepted_bid else order.delivery_fee,
            "ordered_at": order.dateTime,
            "delivered_at": order.delivered_at,
            "items": items,
            "items_count": sum(od.quantity for od in order.ordered_dishes),
            "rating": review.rating if review else None,
            "review_text": review.review_text if review else None,
            "on_time": review.on_time if review else None,
            "has_review": review is not None
        })
    
    return {
        "deliveries": result,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.get("/stats")
async def get_delivery_stats(
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_delivery_person)
):
    """
    Get aggregate statistics for the delivery person.
    """
    # Get delivery rating
    rating = db.query(DeliveryRating).filter(
        DeliveryRating.accountID == current_user.ID
    ).first()
    
    # Calculate on-time percentage
    on_time_percentage = 0.0
    if rating and rating.total_deliveries > 0:
        on_time_percentage = (rating.on_time_deliveries / rating.total_deliveries) * 100
    
    # Get recent reviews
    recent_reviews = db.query(OrderDeliveryReview).filter(
        OrderDeliveryReview.delivery_person_id == current_user.ID
    ).order_by(desc(OrderDeliveryReview.id)).limit(5).all()
    
    reviews_list = [
        {
            "order_id": r.order_id,
            "rating": r.rating,
            "review_text": r.review_text,
            "on_time": r.on_time,
            "created_at": r.created_at
        }
        for r in recent_reviews
    ]
    
    # Get counts
    total_bids = db.query(Bid).filter(Bid.deliveryPersonID == current_user.ID).count()
    
    accepted_bid_ids = db.query(Bid.id).filter(
        Bid.deliveryPersonID == current_user.ID
    ).subquery()
    
    pending_deliveries = db.query(Order).filter(
        Order.bidID.in_(accepted_bid_ids),
        Order.status.in_(["assigned", "out_for_delivery", "preparing", "ready"])
    ).count()
    
    return {
        "account_id": current_user.ID,
        "email": current_user.email,
        "average_rating": float(rating.averageRating) if rating else 0.0,
        "total_reviews": rating.reviews if rating else 0,
        "total_deliveries": rating.total_deliveries if rating else 0,
        "on_time_deliveries": rating.on_time_deliveries if rating else 0,
        "on_time_percentage": round(on_time_percentage, 1),
        "avg_delivery_minutes": rating.avg_delivery_minutes if rating else 30,
        "warnings": current_user.warnings,
        "total_bids": total_bids,
        "pending_deliveries": pending_deliveries,
        "recent_reviews": reviews_list
    }
