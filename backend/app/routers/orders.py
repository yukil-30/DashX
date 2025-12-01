"""
Orders Router - Handles ordering flow
GET /orders - List user's orders
POST /orders - Create order
GET /orders/{id} - Get order details
POST /orders/{id}/bid - Submit delivery bid
GET /orders/{id}/bids - List bids for order
POST /orders/{id}/assign - Manager assigns delivery
"""

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import get_current_user, require_manager
from app.models import Account, Order, OrderedDish, Dish, Bid, Transaction
from app.schemas import (
    OrderCreateRequest,
    OrderResponse,
    OrderCreateResponse,
    OrderedDishResponse,
    InsufficientDepositError,
    BidCreateRequest,
    BidResponse,
    BidListResponse,
    AssignDeliveryRequest,
    AssignDeliveryResponse,
)

router = APIRouter(prefix="/orders", tags=["Orders"])

# Configuration constants
DELIVERY_FEE_CENTS = 500  # $5.00 delivery fee
VIP_DISCOUNT_PERCENT = 5  # 5% discount for VIP customers
VIP_FREE_DELIVERY_EVERY_N_ORDERS = 3  # Free delivery credit every N orders
MAX_ITEMS_PER_ORDER = 50  # Maximum number of items in a single order
MAX_QUANTITY_PER_ITEM = 100  # Maximum quantity per item


def create_transaction(
    db: Session,
    account: Account,
    amount_cents: int,
    transaction_type: str,
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None,
    description: Optional[str] = None
) -> Transaction:
    """Create an audit log entry for a balance change"""
    balance_before = account.balance
    balance_after = account.balance + amount_cents
    
    transaction = Transaction(
        accountID=account.ID,
        amount_cents=amount_cents,
        balance_before=balance_before,
        balance_after=balance_after,
        transaction_type=transaction_type,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        created_at=datetime.now(timezone.utc).isoformat()
    )
    db.add(transaction)
    return transaction


@router.get("", response_model=List[OrderResponse])
async def list_orders(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Max orders to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    List orders for the current user.
    Managers can see all orders.
    Delivery personnel can see orders they have bid on or been assigned to.
    """
    query = db.query(Order).options(
        joinedload(Order.ordered_dishes).joinedload(OrderedDish.dish)
    )
    
    if current_user.type == "manager":
        # Managers see all orders
        pass
    elif current_user.type == "delivery":
        # Delivery personnel see orders they've bid on or been assigned
        bid_order_ids = db.query(Bid.orderID).filter(
            Bid.deliveryPersonID == current_user.ID
        ).subquery()
        query = query.filter(
            (Order.id.in_(bid_order_ids)) | 
            (Order.bidID.in_(
                db.query(Bid.id).filter(Bid.deliveryPersonID == current_user.ID)
            ))
        )
    else:
        # Customers see their own orders
        query = query.filter(Order.accountID == current_user.ID)
    
    if status_filter:
        query = query.filter(Order.status == status_filter)
    
    orders = query.order_by(Order.id.desc()).offset(offset).limit(limit).all()
    
    result = []
    for order in orders:
        ordered_dishes_response = [
            OrderedDishResponse(
                DishID=od.DishID,
                quantity=od.quantity,
                dish_name=od.dish.name if od.dish else None,
                dish_cost=od.dish.cost if od.dish else None
            )
            for od in order.ordered_dishes
        ]
        result.append(OrderResponse(
            id=order.id,
            accountID=order.accountID,
            dateTime=order.dateTime,
            finalCost=order.finalCost,
            status=order.status,
            bidID=order.bidID,
            note=order.note,
            delivery_address=order.delivery_address,
            delivery_fee=order.delivery_fee,
            subtotal_cents=order.subtotal_cents,
            discount_cents=order.discount_cents,
            free_delivery_used=order.free_delivery_used,
            ordered_dishes=ordered_dishes_response
        ))
    
    return result


@router.post("", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_request: OrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Create a new order.
    
    - Computes total_cents from dish costs
    - VIP customers get 5% discount
    - VIP free delivery: every 3 completed orders grants 1 free delivery credit
    - Checks if user has sufficient deposit
    - If insufficient: rejects, increments warnings, returns specific error
    - If sufficient: deducts deposit, creates order with status 'paid'
    """
    # Verify user is a customer/VIP (not employee)
    if current_user.type not in ["customer", "vip", "visitor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can place orders"
        )
    
    # Validate item count
    if len(order_request.items) > MAX_ITEMS_PER_ORDER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_ITEMS_PER_ORDER} different items per order allowed"
        )
    
    # Validate quantities
    for item in order_request.items:
        if item.qty > MAX_QUANTITY_PER_ITEM:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum quantity per item is {MAX_QUANTITY_PER_ITEM}"
            )
    
    # Validate and fetch all dishes
    dish_ids = [item.dish_id for item in order_request.items]
    
    # Check for duplicates
    if len(dish_ids) != len(set(dish_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate dish IDs in order. Combine quantities instead."
        )
    dishes = db.query(Dish).filter(Dish.id.in_(dish_ids)).all()
    dish_map = {dish.id: dish for dish in dishes}
    
    # Check all dishes exist
    for item in order_request.items:
        if item.dish_id not in dish_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dish with id {item.dish_id} not found"
            )
    
    # Calculate subtotal
    subtotal_cents = sum(
        dish_map[item.dish_id].cost * item.qty 
        for item in order_request.items
    )
    
    # Calculate VIP discount
    is_vip = current_user.type == "vip"
    discount_cents = 0
    if is_vip:
        discount_cents = (subtotal_cents * VIP_DISCOUNT_PERCENT) // 100
    
    # Determine delivery fee
    delivery_fee = DELIVERY_FEE_CENTS
    free_delivery_used = 0
    if is_vip and current_user.free_delivery_credits > 0:
        # Use a free delivery credit
        delivery_fee = 0
        free_delivery_used = 1
    
    # Calculate final cost
    final_cost = subtotal_cents - discount_cents + delivery_fee
    
    # Check if user has sufficient deposit
    if current_user.balance < final_cost:
        # Insufficient funds - increment warning and reject
        current_user.warnings += 1
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "insufficient_deposit",
                "warnings": current_user.warnings,
                "required_amount": final_cost,
                "current_balance": current_user.balance,
                "shortfall": final_cost - current_user.balance
            }
        )
    
    # === Transactional order creation ===
    try:
        # Create the order
        order = Order(
            accountID=current_user.ID,
            dateTime=datetime.now(timezone.utc).isoformat(),
            finalCost=final_cost,
            status="paid",  # Immediately paid since deposit is sufficient
            note=order_request.note,
            delivery_address=order_request.delivery_address,
            delivery_fee=delivery_fee,
            subtotal_cents=subtotal_cents,
            discount_cents=discount_cents,
            free_delivery_used=free_delivery_used
        )
        db.add(order)
        db.flush()  # Get order.id
        
        # Create ordered dishes
        for item in order_request.items:
            ordered_dish = OrderedDish(
                DishID=item.dish_id,
                orderID=order.id,
                quantity=item.qty
            )
            db.add(ordered_dish)
        
        # Deduct from user balance (audit logged)
        create_transaction(
            db=db,
            account=current_user,
            amount_cents=-final_cost,
            transaction_type="order_payment",
            reference_type="order",
            reference_id=order.id,
            description=f"Payment for order #{order.id}"
        )
        current_user.balance -= final_cost
        
        # If VIP used free delivery, deduct the credit
        if free_delivery_used:
            current_user.free_delivery_credits -= 1
        
        # Increment completed orders count for VIP
        # (We count 'paid' orders towards free delivery credits)
        if is_vip:
            current_user.completed_orders_count += 1
            # Check if VIP earns a new free delivery credit
            if current_user.completed_orders_count % VIP_FREE_DELIVERY_EVERY_N_ORDERS == 0:
                current_user.free_delivery_credits += 1
        
        db.commit()
        db.refresh(order)
        
        # Build response with dish details
        ordered_dishes_response = []
        for od in order.ordered_dishes:
            dish = dish_map.get(od.DishID)
            ordered_dishes_response.append(OrderedDishResponse(
                DishID=od.DishID,
                quantity=od.quantity,
                dish_name=dish.name if dish else None,
                dish_cost=dish.cost if dish else None
            ))
        
        return OrderCreateResponse(
            message="Order created successfully",
            order=OrderResponse(
                id=order.id,
                accountID=order.accountID,
                dateTime=order.dateTime,
                finalCost=order.finalCost,
                status=order.status,
                bidID=order.bidID,
                note=order.note,
                delivery_address=order.delivery_address,
                delivery_fee=order.delivery_fee,
                subtotal_cents=order.subtotal_cents,
                discount_cents=order.discount_cents,
                free_delivery_used=order.free_delivery_used,
                ordered_dishes=ordered_dishes_response
            ),
            balance_deducted=final_cost,
            new_balance=current_user.balance
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """Get order details by ID"""
    order = db.query(Order).options(
        joinedload(Order.ordered_dishes).joinedload(OrderedDish.dish)
    ).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )
    
    # Authorization: owner, delivery person, or manager can view
    is_owner = order.accountID == current_user.ID
    is_manager = current_user.type == "manager"
    is_delivery = current_user.type == "delivery"
    
    if not (is_owner or is_manager or is_delivery):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Build response with dish details
    ordered_dishes_response = []
    for od in order.ordered_dishes:
        ordered_dishes_response.append(OrderedDishResponse(
            DishID=od.DishID,
            quantity=od.quantity,
            dish_name=od.dish.name if od.dish else None,
            dish_cost=od.dish.cost if od.dish else None
        ))
    
    return OrderResponse(
        id=order.id,
        accountID=order.accountID,
        dateTime=order.dateTime,
        finalCost=order.finalCost,
        status=order.status,
        bidID=order.bidID,
        note=order.note,
        delivery_address=order.delivery_address,
        delivery_fee=order.delivery_fee,
        subtotal_cents=order.subtotal_cents,
        discount_cents=order.discount_cents,
        free_delivery_used=order.free_delivery_used,
        ordered_dishes=ordered_dishes_response
    )


@router.post("/{order_id}/bid", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def create_bid(
    order_id: int,
    bid_request: BidCreateRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    Submit a delivery bid for an order.
    Only delivery personnel can submit bids.
    Order must be in 'paid' status (open for bidding).
    """
    # Only delivery personnel can bid
    if current_user.type != "delivery":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only delivery personnel can submit bids"
        )
    
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
        bidAmount=bid_request.price_cents
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)
    
    return BidResponse(
        id=bid.id,
        deliveryPersonID=bid.deliveryPersonID,
        orderID=bid.orderID,
        bidAmount=bid.bidAmount,
        delivery_person_email=current_user.email
    )


@router.get("/{order_id}/bids", response_model=BidListResponse)
async def list_bids(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """
    List all bids for an order, sorted by bid amount (lowest first).
    Accessible by order owner, manager, or delivery personnel.
    """
    # Get order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )
    
    # Authorization check
    is_owner = order.accountID == current_user.ID
    is_manager = current_user.type == "manager"
    is_delivery = current_user.type == "delivery"
    
    if not (is_owner or is_manager or is_delivery):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get all bids with delivery person info, sorted by bid amount
    bids = db.query(Bid).options(
        joinedload(Bid.delivery_person)
    ).filter(Bid.orderID == order_id).order_by(Bid.bidAmount.asc()).all()
    
    bid_responses = [
        BidResponse(
            id=bid.id,
            deliveryPersonID=bid.deliveryPersonID,
            orderID=bid.orderID,
            bidAmount=bid.bidAmount,
            delivery_person_email=bid.delivery_person.email if bid.delivery_person else None
        )
        for bid in bids
    ]
    
    return BidListResponse(
        order_id=order_id,
        bids=bid_responses
    )


@router.post("/{order_id}/assign", response_model=AssignDeliveryResponse)
async def assign_delivery(
    order_id: int,
    assign_request: AssignDeliveryRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(require_manager)
):
    """
    Manager assigns a delivery person to an order.
    The delivery person must have a bid on this order.
    Updates order status to 'assigned' and sets bidID.
    """
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
            detail=f"Cannot assign delivery. Order status is '{order.status}', must be 'paid'"
        )
    
    # Verify delivery person exists and is a delivery account
    delivery_person = db.query(Account).filter(Account.ID == assign_request.delivery_id).first()
    if not delivery_person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery person with ID {assign_request.delivery_id} not found"
        )
    if delivery_person.type != "delivery":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specified account is not a delivery person"
        )
    
    # Find the bid from this delivery person
    bid = db.query(Bid).filter(
        Bid.orderID == order_id,
        Bid.deliveryPersonID == assign_request.delivery_id
    ).first()
    
    if not bid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery person has not submitted a bid for this order"
        )
    
    # Update order
    order.bidID = bid.id
    order.status = "assigned"
    if assign_request.memo:
        order.note = (order.note or "") + f"\n[Manager Assignment]: {assign_request.memo}"
    
    db.commit()
    db.refresh(order)
    
    return AssignDeliveryResponse(
        message="Delivery assigned successfully",
        order_id=order.id,
        assigned_delivery_id=assign_request.delivery_id,
        bid_id=bid.id,
        delivery_fee=bid.bidAmount,
        order_status=order.status
    )
