"""
Reputation & HR Router
Handles complaints, compliments, warnings, and reputation management

Business Rules:
- Registered customers with 3 warnings -> deregistered and blacklisted
- VIP with 2 warnings -> revert to registered and clear warnings
- Chef with 3 complaints OR average dish rating <2 -> demotion (decrement salary, increment times_demoted)
- Chef demoted twice -> fired
- Compliments can cancel complaints one-for-one
- Dismissed complaints (without merit) add warning to complainant
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Account, Complaint, AuditLog, Blacklist, ManagerNotification, Dish, Order, OrderedDish, Bid, DeliveryRating
from app.schemas import (
    ComplaintCreateRequest, ComplaintResponse, ComplaintListResponse,
    ComplaintResolveRequest, ComplaintResolveResponse,
    AuditLogResponse, AuditLogListResponse,
    ManagerNotificationResponse, ManagerNotificationListResponse,
    DisputeRequest, DisputeResponse,
    EmployeeReputationSummary, CustomerWarningSummary, ReputationDashboardStats,
    EmployeeListWithReputationResponse, CustomerListWithWarningsResponse,
    DisputeDetailResponse, DisputeResolveRequest as NewDisputeResolveRequest, DisputeResolveResponse as NewDisputeResolveResponse
)
from app.auth import get_current_user, require_manager
from app import reputation_engine as rep_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/complaints", tags=["Reputation & HR"])


# ============================================================
# Helper Functions
# ============================================================

def get_iso_now() -> str:
    """Get current timestamp as ISO string"""
    return datetime.now(timezone.utc).isoformat()


def create_audit_entry(
    db: Session,
    action_type: str,
    actor_id: Optional[int] = None,
    target_id: Optional[int] = None,
    complaint_id: Optional[int] = None,
    order_id: Optional[int] = None,
    details: Optional[dict] = None
) -> AuditLog:
    """Create an immutable audit log entry"""
    entry = AuditLog(
        action_type=action_type,
        actor_id=actor_id,
        target_id=target_id,
        complaint_id=complaint_id,
        order_id=order_id,
        details=details,
        created_at=get_iso_now()
    )
    db.add(entry)
    db.flush()
    return entry


def create_manager_notification(
    db: Session,
    notification_type: str,
    title: str,
    message: str,
    related_account_id: Optional[int] = None,
    related_order_id: Optional[int] = None
) -> ManagerNotification:
    """Create a notification for managers"""
    notification = ManagerNotification(
        notification_type=notification_type,
        title=title,
        message=message,
        related_account_id=related_account_id,
        related_order_id=related_order_id,
        is_read=False,
        created_at=get_iso_now()
    )
    db.add(notification)
    db.flush()
    return notification


def check_and_apply_customer_warning_rules(db: Session, account: Account, manager_id: int) -> Optional[str]:
    """
    Apply warning rules for customers/VIPs:
    - Registered customer with 3 warnings -> blacklisted
    - VIP with 2 warnings -> demote to registered, clear warnings
    
    Returns status change message or None
    """
    if account.type == "customer" and account.warnings >= 3:
        # Blacklist the customer
        account.is_blacklisted = True
        account.type = "blacklisted"
        
        # Add to blacklist table
        blacklist_entry = Blacklist(
            email=account.email,
            reason=f"Reached 3 warnings. Automatically deregistered.",
            original_account_id=account.ID,
            blacklisted_by=manager_id,
            created_at=get_iso_now()
        )
        db.add(blacklist_entry)
        
        create_audit_entry(
            db,
            action_type="customer_blacklisted",
            actor_id=manager_id,
            target_id=account.ID,
            details={"warnings": account.warnings, "reason": "3 warnings threshold"}
        )
        
        create_manager_notification(
            db,
            notification_type="customer_blacklisted",
            title=f"Customer Blacklisted",
            message=f"Customer {account.email} has been blacklisted after reaching 3 warnings.",
            related_account_id=account.ID
        )
        
        return "blacklisted"
    
    elif account.type == "vip" and account.warnings >= 2:
        # Demote VIP to customer and clear warnings
        account.previous_type = "vip"
        account.type = "customer"
        old_warnings = account.warnings
        account.warnings = 0
        
        create_audit_entry(
            db,
            action_type="vip_demoted",
            actor_id=manager_id,
            target_id=account.ID,
            details={"from_type": "vip", "to_type": "customer", "warnings_cleared": old_warnings}
        )
        
        create_manager_notification(
            db,
            notification_type="vip_demoted",
            title=f"VIP Demoted",
            message=f"VIP {account.email} has been demoted to regular customer after reaching 2 warnings.",
            related_account_id=account.ID
        )
        
        return "vip_demoted_to_customer"
    
    return None


def check_and_apply_chef_rules(db: Session, chef: Account, manager_id: int) -> Optional[str]:
    """
    Apply rules for chefs:
    - 3 complaints OR average dish rating <2 -> demotion
    - Demoted twice -> fired
    
    Returns status change message or None
    """
    if chef.type != "chef" or chef.is_fired:
        return None
    
    # Count unresolved complaints about this chef
    complaint_count = db.query(Complaint).filter(
        Complaint.accountID == chef.ID,
        Complaint.type == "complaint",
        Complaint.status == "resolved",
        Complaint.resolution == "warning_issued"
    ).count()
    
    # Calculate average dish rating for this chef
    avg_rating_result = db.query(func.avg(Dish.average_rating)).filter(
        Dish.chefID == chef.ID,
        Dish.reviews > 0  # Only count dishes that have been rated
    ).scalar()
    
    avg_rating = float(avg_rating_result) if avg_rating_result else 5.0  # Default to good rating if no reviews
    
    should_demote = complaint_count >= 3 or avg_rating < 2.0
    
    if should_demote:
        chef.times_demoted += 1
        
        if chef.times_demoted >= 2:
            # Fire the chef
            chef.is_fired = True
            chef.previous_type = chef.type
            chef.type = "fired"
            
            create_audit_entry(
                db,
                action_type="chef_fired",
                actor_id=manager_id,
                target_id=chef.ID,
                details={
                    "times_demoted": chef.times_demoted,
                    "complaint_count": complaint_count,
                    "avg_rating": avg_rating
                }
            )
            
            create_manager_notification(
                db,
                notification_type="chef_fired",
                title=f"Chef Fired",
                message=f"Chef {chef.email} has been fired after 2 demotions.",
                related_account_id=chef.ID
            )
            
            return "chef_fired"
        else:
            # Demote: reduce wage by 10%
            if chef.wage:
                old_wage = chef.wage
                chef.wage = int(chef.wage * 0.9)
            else:
                old_wage = None
            
            create_audit_entry(
                db,
                action_type="chef_demoted",
                actor_id=manager_id,
                target_id=chef.ID,
                details={
                    "times_demoted": chef.times_demoted,
                    "complaint_count": complaint_count,
                    "avg_rating": avg_rating,
                    "old_wage": old_wage,
                    "new_wage": chef.wage
                }
            )
            
            create_manager_notification(
                db,
                notification_type="chef_demoted",
                title=f"Chef Demoted",
                message=f"Chef {chef.email} has been demoted (time #{chef.times_demoted}). Wage reduced.",
                related_account_id=chef.ID
            )
            
            return "chef_demoted"
    
    return None


def check_compliment_cancellation(db: Session, account: Account, manager_id: int) -> int:
    """
    Check if compliments can cancel complaints for this account.
    Returns number of complaints canceled.
    """
    # Count pending compliments
    compliments = db.query(Complaint).filter(
        Complaint.accountID == account.ID,
        Complaint.type == "compliment",
        Complaint.status == "pending"
    ).all()
    
    # Count pending complaints
    complaints = db.query(Complaint).filter(
        Complaint.accountID == account.ID,
        Complaint.type == "complaint",
        Complaint.status == "pending"
    ).order_by(Complaint.created_at.asc()).all()
    
    canceled_count = 0
    
    # Cancel one complaint per compliment
    for i, compliment in enumerate(compliments):
        if i < len(complaints):
            complaint = complaints[i]
            
            # Mark both as resolved
            compliment.status = "resolved"
            compliment.resolution = "canceled_complaint"
            compliment.resolved_by = manager_id
            compliment.resolved_at = get_iso_now()
            
            complaint.status = "resolved"
            complaint.resolution = "canceled_by_compliment"
            complaint.resolved_by = manager_id
            complaint.resolved_at = get_iso_now()
            
            create_audit_entry(
                db,
                action_type="complaint_canceled_by_compliment",
                actor_id=manager_id,
                target_id=account.ID,
                complaint_id=complaint.id,
                details={"compliment_id": compliment.id}
            )
            
            canceled_count += 1
    
    return canceled_count


# ============================================================
# Complaint Endpoints
# ============================================================

def validate_complaint_filing(
    db: Session,
    filer: Account,
    target: Account,
    order_id: Optional[int],
    target_type: Optional[str]
) -> str:
    """
    Validate that the filer can file a complaint against the target.
    
    Filing rules:
    - Customer can file against: chef (of dish they ordered), delivery person (who delivered their order)
    - Delivery person can file against: customers (whose orders they delivered)
    
    Returns the validated target_type or raises HTTPException.
    """
    filer_is_customer = filer.type in ["customer", "vip", "visitor"]
    filer_is_delivery = filer.type == "delivery"
    target_is_customer = target.type in ["customer", "vip"]
    target_is_chef = target.type == "chef"
    target_is_delivery = target.type == "delivery"
    
    # Validate customer filing against chef
    if filer_is_customer and target_is_chef:
        if not order_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order ID required when filing complaint against a chef"
            )
        # Verify customer ordered from this chef
        order = db.query(Order).filter(Order.id == order_id, Order.accountID == filer.ID).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can only file complaints about orders you placed"
            )
        # Verify the chef made dishes in this order
        ordered_dishes = db.query(OrderedDish).filter(OrderedDish.orderID == order_id).all()
        dish_ids = [od.DishID for od in ordered_dishes]
        from app.models import Dish
        chef_dishes = db.query(Dish).filter(Dish.id.in_(dish_ids), Dish.chefID == target.ID).count()
        if chef_dishes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This chef did not prepare any dishes in your order"
            )
        return "chef"
    
    # Validate customer filing against delivery person
    if filer_is_customer and target_is_delivery:
        if not order_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order ID required when filing complaint against a delivery person"
            )
        # Verify this delivery person delivered the customer's order
        order = db.query(Order).filter(Order.id == order_id, Order.accountID == filer.ID).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can only file complaints about orders you placed"
            )
        if not order.bidID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This order has no assigned delivery person"
            )
        bid = db.query(Bid).filter(Bid.id == order.bidID).first()
        if not bid or bid.deliveryPersonID != target.ID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This delivery person did not deliver your order"
            )
        return "delivery"
    
    # Validate delivery person filing against customer
    if filer_is_delivery and target_is_customer:
        if not order_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order ID required when filing complaint against a customer"
            )
        # Verify the delivery person delivered this customer's order
        order = db.query(Order).filter(Order.id == order_id, Order.accountID == target.ID).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This order does not belong to the specified customer"
            )
        if not order.bidID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This order has no assigned delivery person"
            )
        bid = db.query(Bid).filter(Bid.id == order.bidID).first()
        if not bid or bid.deliveryPersonID != filer.ID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You did not deliver this order"
            )
        return "customer"
    
    # Manager can file against anyone
    if filer.type == "manager":
        return target_type or target.type
    
    # Invalid combination
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"User type '{filer.type}' cannot file complaints against user type '{target.type}'"
    )


@router.post("", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def file_complaint(
    request: ComplaintCreateRequest,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    File a complaint or compliment.
    
    Filing rules:
    - Customer can file against: chef (of dish they ordered), delivery person (who delivered their order)
    - Delivery person can file against: customers (whose orders they delivered)
    - Manager can file against anyone
    
    Parameters:
    - about_user_id: User being complained about (null for general complaints)
    - order_id: Related order (required for most complaint types)
    - type: 'complaint' or 'compliment'
    - text: Description
    - target_type: Role of person being complained about (optional, auto-detected)
    """
    # Validate about_user_id if provided
    about_account = None
    validated_target_type = None
    
    if request.about_user_id:
        # Prevent self-complaints
        if request.about_user_id == current_user.ID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot file a complaint about yourself"
            )
        
        about_account = db.query(Account).filter(Account.ID == request.about_user_id).first()
        if not about_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User being complained about not found"
            )
        
        # Validate filing rules
        validated_target_type = validate_complaint_filing(
            db, current_user, about_account, request.order_id, request.target_type
        )
    
    # Create complaint
    complaint = Complaint(
        accountID=request.about_user_id,
        type=request.type,
        description=request.text,
        filer=current_user.ID,
        order_id=request.order_id,
        status="pending",
        target_type=validated_target_type,
        disputed=False,
        created_at=get_iso_now()
    )
    db.add(complaint)
    db.flush()
    
    # Create audit entry
    create_audit_entry(
        db,
        action_type=f"{request.type}_filed",
        actor_id=current_user.ID,
        target_id=request.about_user_id,
        complaint_id=complaint.id,
        order_id=request.order_id,
        details={"type": request.type, "target_type": validated_target_type}
    )
    
    db.commit()
    db.refresh(complaint)
    
    logger.info(f"{request.type.capitalize()} filed by {current_user.email} about user {request.about_user_id}")
    
    return ComplaintResponse(
        id=complaint.id,
        accountID=complaint.accountID,
        type=complaint.type,
        description=complaint.description,
        filer=complaint.filer,
        filer_email=current_user.email,
        about_email=about_account.email if about_account else None,
        order_id=complaint.order_id,
        status=complaint.status,
        resolution=complaint.resolution,
        resolved_by=complaint.resolved_by,
        resolved_at=complaint.resolved_at,
        created_at=complaint.created_at.isoformat() if hasattr(complaint.created_at, "isoformat") else complaint.created_at,
        disputed=complaint.disputed if complaint.disputed is not None else False,
        dispute_reason=complaint.dispute_reason,
        disputed_at=complaint.disputed_at,
        target_type=complaint.target_type
    )


@router.get("", response_model=ComplaintListResponse)
async def list_complaints(
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, resolved"),
    type_filter: Optional[str] = Query(None, description="Filter by type: complaint, compliment"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    List complaints (manager only).
    """
    query = db.query(Complaint)
    
    if status_filter:
        query = query.filter(Complaint.status == status_filter)
    if type_filter:
        query = query.filter(Complaint.type == type_filter)
    
    total = query.count()
    unresolved_count = db.query(Complaint).filter(Complaint.status == "pending").count()
    
    complaints = query.order_by(Complaint.created_at.desc()).offset(offset).limit(limit).all()
    
    # Build response with email lookups
    response_complaints = []
    for c in complaints:
        filer_account = db.query(Account).filter(Account.ID == c.filer).first()
        about_account = db.query(Account).filter(Account.ID == c.accountID).first() if c.accountID else None
        
        response_complaints.append(ComplaintResponse(
            id=c.id,
            accountID=c.accountID,
            type=c.type,
            description=c.description,
            filer=c.filer,
            filer_email=filer_account.email if filer_account else None,
            about_email=about_account.email if about_account else None,
            order_id=c.order_id,
            status=c.status,
            resolution=c.resolution,
            resolved_by=c.resolved_by,
            resolved_at=c.resolved_at,
            created_at=c.created_at.isoformat() if hasattr(c.created_at, "isoformat") else c.created_at,
            disputed=c.disputed if c.disputed is not None else False,
            dispute_reason=c.dispute_reason,
            disputed_at=c.disputed_at,
            target_type=c.target_type
        ))
    
    return ComplaintListResponse(
        complaints=response_complaints,
        total=total,
        unresolved_count=unresolved_count
    )


@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(
    complaint_id: int,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Get a single complaint by ID (manager only)."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    filer_account = db.query(Account).filter(Account.ID == complaint.filer).first()
    about_account = db.query(Account).filter(Account.ID == complaint.accountID).first() if complaint.accountID else None
    
    return ComplaintResponse(
        id=complaint.id,
        accountID=complaint.accountID,
        type=complaint.type,
        description=complaint.description,
        filer=complaint.filer,
        filer_email=filer_account.email if filer_account else None,
        about_email=about_account.email if about_account else None,
        order_id=complaint.order_id,
        status=complaint.status,
        resolution=complaint.resolution,
        resolved_by=complaint.resolved_by,
        resolved_at=complaint.resolved_at,
        created_at=complaint.created_at.isoformat() if hasattr(complaint.created_at, "isoformat") else complaint.created_at,
        disputed=complaint.disputed if complaint.disputed is not None else False,
        dispute_reason=complaint.dispute_reason,
        disputed_at=complaint.disputed_at,
        target_type=complaint.target_type
    )


@router.post("/{complaint_id}/dispute", response_model=DisputeResponse)
async def dispute_complaint(
    complaint_id: int,
    request: DisputeRequest,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dispute a complaint filed against you.
    
    Anyone receiving a complaint can dispute it.
    Disputed complaints move to the manager queue for resolution.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    # Only the person complained about can dispute
    if complaint.accountID != current_user.ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only dispute complaints filed against you"
        )
    
    # Can't dispute compliments
    if complaint.type == "compliment":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot dispute a compliment"
        )
    
    # Can't dispute already resolved complaints
    if complaint.status == "resolved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot dispute an already resolved complaint"
        )
    
    # Can't dispute twice
    if complaint.disputed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This complaint has already been disputed"
        )
    
    # Mark as disputed
    complaint.disputed = True
    complaint.dispute_reason = request.reason
    complaint.disputed_at = get_iso_now()
    complaint.status = "disputed"
    
    # Create audit entry
    create_audit_entry(
        db,
        action_type="complaint_disputed",
        actor_id=current_user.ID,
        target_id=complaint.filer,
        complaint_id=complaint.id,
        details={"reason": request.reason}
    )
    
    # Notify managers
    filer = db.query(Account).filter(Account.ID == complaint.filer).first()
    create_manager_notification(
        db,
        notification_type="complaint_disputed",
        title="Complaint Disputed",
        message=f"Complaint #{complaint.id} by {filer.email if filer else 'unknown'} has been disputed by {current_user.email}",
        related_account_id=current_user.ID
    )
    
    db.commit()
    
    logger.info(f"Complaint {complaint_id} disputed by {current_user.email}")
    
    return DisputeResponse(
        message="Complaint has been disputed and sent to manager queue",
        complaint_id=complaint.id,
        disputed=True,
        dispute_reason=request.reason,
        status="disputed",
        disputed_at=complaint.disputed_at
    )


@router.get("/my/filed", response_model=ComplaintListResponse)
async def get_my_filed_complaints(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get complaints/compliments filed by the current user."""
    query = db.query(Complaint).filter(Complaint.filer == current_user.ID)
    
    total = query.count()
    unresolved_count = query.filter(Complaint.status == "pending").count()
    
    complaints = query.order_by(Complaint.created_at.desc()).offset(offset).limit(limit).all()
    
    response_complaints = []
    for c in complaints:
        about_account = db.query(Account).filter(Account.ID == c.accountID).first() if c.accountID else None
        
        response_complaints.append(ComplaintResponse(
            id=c.id,
            accountID=c.accountID,
            type=c.type,
            description=c.description,
            filer=c.filer,
            filer_email=current_user.email,
            about_email=about_account.email if about_account else None,
            order_id=c.order_id,
            status=c.status,
            resolution=c.resolution,
            resolved_by=c.resolved_by,
            resolved_at=c.resolved_at.isoformat() if hasattr(c.resolved_at, "isoformat") else c.resolved_at,
            created_at=c.created_at.isoformat() if hasattr(c.created_at, "isoformat") else c.created_at,
            disputed=c.disputed if c.disputed is not None else False,
            dispute_reason=c.dispute_reason,
            disputed_at=c.disputed_at,
            target_type=c.target_type
        ))
    
    return ComplaintListResponse(
        complaints=response_complaints,
        total=total,
        unresolved_count=unresolved_count
    )


@router.get("/my/against", response_model=ComplaintListResponse)
async def get_complaints_against_me(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get complaints/compliments filed against the current user."""
    query = db.query(Complaint).filter(Complaint.accountID == current_user.ID)
    
    total = query.count()
    unresolved_count = query.filter(Complaint.status == "pending").count()
    
    complaints = query.order_by(Complaint.created_at.desc()).offset(offset).limit(limit).all()
    
    response_complaints = []
    for c in complaints:
        filer_account = db.query(Account).filter(Account.ID == c.filer).first()
        
        response_complaints.append(ComplaintResponse(
            id=c.id,
            accountID=c.accountID,
            type=c.type,
            description=c.description,
            filer=c.filer,
            filer_email=filer_account.email if filer_account else None,
            about_email=current_user.email,
            order_id=c.order_id,
            status=c.status,
            resolution=c.resolution,
            resolved_by=c.resolved_by,
            resolved_at=c.resolved_at.isoformat() if hasattr(c.resolved_at, "isoformat") else c.resolved_at,
            created_at=c.created_at.isoformat() if hasattr(c.created_at, "isoformat") else c.created_at,
            disputed=c.disputed if c.disputed is not None else False,
            dispute_reason=c.dispute_reason,
            disputed_at=c.disputed_at,
            target_type=c.target_type
        ))
    
    return ComplaintListResponse(
        complaints=response_complaints,
        total=total,
        unresolved_count=unresolved_count
    )


@router.patch("/{complaint_id}/resolve", response_model=ComplaintResolveResponse)
async def resolve_complaint(
    complaint_id: int,
    request: ComplaintResolveRequest,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Resolve a complaint (manager only).
    
    - dismissed: Complaint without merit -> complainant gets a warning
    - warning_issued: Valid complaint -> target gets a warning
    
    Uses the reputation engine for rule evaluation and automatic actions.
    Produces an immutable audit entry.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    if complaint.status == "resolved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint already resolved"
        )
    
    # Handle compliment resolution separately
    if complaint.type == "compliment":
        result = rep_engine.process_compliment_resolution(db, complaint, current_user.ID)
        db.commit()
        
        # Create audit entry
        audit_entry = rep_engine.create_audit_entry(
            db,
            action_type="compliment_resolved",
            actor_id=current_user.ID,
            complaint_id=complaint.id,
            details={"actions": result.get("actions", [])}
        )
        db.commit()
        
        return ComplaintResolveResponse(
            message="Compliment resolved and benefits applied",
            complaint_id=complaint.id,
            resolution="compliment_applied",
            warning_applied_to=None,
            warning_count=None,
            account_status_changed=None,
            audit_log_id=audit_entry.id
        )
    
    # Use reputation engine for dispute resolution
    result = rep_engine.resolve_dispute(
        db, complaint, request.resolution, current_user.ID, request.notes
    )
    
    # Extract results
    warning_applied_to = result.get("warning_applied_to")
    warning_count = None
    account_status_changed = None
    
    # Check what happened
    for action in result.get("actions", []):
        if "rule_results" in action:
            rule_results = action["rule_results"]
            if rule_results.get("demoted"):
                account_status_changed = "employee_demoted"
            elif rule_results.get("fired"):
                account_status_changed = "employee_fired"
            elif rule_results.get("bonus_awarded"):
                account_status_changed = "bonus_awarded"
            elif rule_results.get("vip_demoted"):
                account_status_changed = "vip_demoted"
            elif rule_results.get("deregistered"):
                account_status_changed = "deregistered"
        
        if "new_warnings" in action:
            warning_count = action["new_warnings"]
    
    # Get warning count if we have a target
    if warning_applied_to and warning_count is None:
        target = db.query(Account).filter(Account.ID == warning_applied_to).first()
        if target:
            warning_count = target.warnings
    
    db.commit()
    
    # Create final audit entry
    audit_entry = rep_engine.create_audit_entry(
        db,
        action_type="complaint_resolved_with_engine",
        actor_id=current_user.ID,
        target_id=warning_applied_to,
        complaint_id=complaint.id,
        order_id=complaint.order_id,
        details={
            "resolution": request.resolution,
            "notes": request.notes,
            "warning_applied_to": warning_applied_to,
            "warning_count": warning_count,
            "account_status_changed": account_status_changed,
            "actions_taken": len(result.get("actions", []))
        }
    )
    db.commit()
    
    logger.info(f"Complaint {complaint_id} resolved as {request.resolution} by {current_user.email}")
    
    return ComplaintResolveResponse(
        message=f"Complaint resolved as {request.resolution}",
        complaint_id=complaint.id,
        resolution=request.resolution,
        warning_applied_to=warning_applied_to,
        warning_count=warning_count,
        account_status_changed=account_status_changed,
        audit_log_id=audit_entry.id
    )


# ============================================================
# Audit Log Endpoints
# ============================================================

@router.get("/audit/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    target_id: Optional[int] = Query(None, description="Filter by target user ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """List audit log entries (manager only)."""
    query = db.query(AuditLog)
    
    if action_type:
        query = query.filter(AuditLog.action_type == action_type)
    if target_id:
        query = query.filter(AuditLog.target_id == target_id)
    
    total = query.count()
    entries = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    
    return AuditLogListResponse(
        entries=[AuditLogResponse(
            id=e.id,
            action_type=e.action_type,
            actor_id=e.actor_id,
            target_id=e.target_id,
            complaint_id=e.complaint_id,
            order_id=e.order_id,
            details=e.details,
            created_at=e.created_at
        ) for e in entries],
        total=total
    )


# ============================================================
# Manager Notification Endpoints
# ============================================================

@router.get("/notifications", response_model=ManagerNotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(False, description="Only show unread notifications"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """List manager notifications."""
    query = db.query(ManagerNotification)
    
    if unread_only:
        query = query.filter(ManagerNotification.is_read == False)
    
    total = query.count()
    unread_count = db.query(ManagerNotification).filter(ManagerNotification.is_read == False).count()
    
    notifications = query.order_by(ManagerNotification.created_at.desc()).offset(offset).limit(limit).all()
    
    return ManagerNotificationListResponse(
        notifications=[ManagerNotificationResponse(
            id=n.id,
            notification_type=n.notification_type,
            title=n.title,
            message=n.message,
            related_account_id=n.related_account_id,
            related_order_id=n.related_order_id,
            is_read=n.is_read,
            created_at=n.created_at
        ) for n in notifications],
        total=total,
        unread_count=unread_count
    )


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Mark a notification as read."""
    notification = db.query(ManagerNotification).filter(ManagerNotification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Notification marked as read"}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read."""
    db.query(ManagerNotification).filter(ManagerNotification.is_read == False).update({"is_read": True})
    db.commit()
    
    return {"message": "All notifications marked as read"}


# ============================================================
# Chef Performance Evaluation Endpoint
# ============================================================

# Add this endpoint to your reputation.py file

@router.get("/my-summary")
async def get_my_complaint_summary(
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get complaint/compliment summary for the current user (chef).
    Returns stats and recent items.
    """
    if current_user.type != "chef":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only chefs can view this summary"
        )
    
    # Count total complaints
    total_complaints = db.query(Complaint).filter(
        Complaint.accountID == current_user.ID,
        Complaint.type == "complaint"
    ).count()
    
    # Count unresolved complaints
    unresolved_complaints = db.query(Complaint).filter(
        Complaint.accountID == current_user.ID,
        Complaint.type == "complaint",
        Complaint.status == "pending"
    ).count()
    
    # Count total compliments
    total_compliments = db.query(Complaint).filter(
        Complaint.accountID == current_user.ID,
        Complaint.type == "compliment"
    ).count()
    
    # Get recent items (last 5)
    recent_items = db.query(Complaint).filter(
        Complaint.accountID == current_user.ID
    ).order_by(Complaint.created_at.desc()).limit(5).all()
    
    # Build response
    recent_items_response = []
    for item in recent_items:
        filer_account = db.query(Account).filter(Account.ID == item.filer).first()
        recent_items_response.append({
            "id": item.id,
            "type": item.type,
            "description": item.description,
            "filer_email": filer_account.email if filer_account else None,
            "order_id": item.order_id,
            "status": item.status,
            "created_at": item.created_at.isoformat() if hasattr(item.created_at, "isoformat") else item.created_at
        })
    
    return {
        "total_complaints": total_complaints,
        "unresolved_complaints": unresolved_complaints,
        "total_compliments": total_compliments,
        "net_score": total_compliments - total_complaints,
        "recent_items": recent_items_response
    }

@router.post("/evaluate/chefs")
async def evaluate_chef_performance(
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Manually trigger chef performance evaluation.
    Checks all chefs for complaint threshold and rating threshold.
    Uses the reputation engine.
    """
    results = rep_engine.run_all_employee_evaluations(db, current_user.ID)
    
    # Filter to just chefs
    chef_results = [r for r in results if r.get("type") == "chef"]
    
    db.commit()
    
    return {
        "message": f"Evaluated {len(chef_results)} chefs",
        "evaluations": chef_results
    }


# ============================================================
# Reputation Dashboard Endpoints
# ============================================================

@router.get("/reputation/dashboard", response_model=ReputationDashboardStats)
async def get_reputation_dashboard(
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive reputation dashboard statistics.
    Shows employee and customer status overview.
    """
    # Employee counts
    employees = db.query(Account).filter(Account.type.in_(["chef", "delivery"]))
    total_employees = employees.count()
    active_employees = employees.filter(Account.is_fired == False, Account.employment_status == "active").count()
    demoted_employees = employees.filter(Account.employment_status == "demoted", Account.is_fired == False).count()
    fired_employees = employees.filter(Account.is_fired == True).count()
    
    # Employees at risk
    employees_near_demotion = db.query(Account).filter(
        Account.type.in_(["chef", "delivery"]),
        Account.is_fired == False,
        ((Account.complaint_count >= 2) | (Account.rolling_avg_rating < 2.5))
    ).count()
    
    employees_near_firing = db.query(Account).filter(
        Account.type.in_(["chef", "delivery"]),
        Account.is_fired == False,
        Account.times_demoted == 1
    ).count()
    
    employees_bonus_eligible = db.query(Account).filter(
        Account.type.in_(["chef", "delivery"]),
        Account.is_fired == False,
        ((Account.compliment_count >= 2) | (Account.rolling_avg_rating > 4.0))
    ).count()
    
    # Customer counts
    customers = db.query(Account).filter(Account.type.in_(["customer", "vip", "visitor"]))
    total_customers = customers.count()
    vip_customers = customers.filter(Account.type == "vip").count()
    customers_with_warnings = customers.filter(Account.warnings > 0).count()
    customers_near_dereg = customers.filter(Account.warnings >= 2, Account.type != "vip").count()
    deregistered = db.query(Account).filter(Account.is_blacklisted == True).count()
    
    # Recent activity (last 7 days)
    from datetime import timedelta
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    
    recent_demotions = db.query(AuditLog).filter(
        AuditLog.action_type.in_(["employee_demoted", "employee_demoted_auto"]),
        AuditLog.created_at >= week_ago
    ).count()
    
    recent_firings = db.query(AuditLog).filter(
        AuditLog.action_type.in_(["employee_fired", "employee_fired_auto"]),
        AuditLog.created_at >= week_ago
    ).count()
    
    recent_bonuses = db.query(AuditLog).filter(
        AuditLog.action_type.in_(["employee_bonus", "employee_bonus_auto"]),
        AuditLog.created_at >= week_ago
    ).count()
    
    recent_warnings = db.query(AuditLog).filter(
        AuditLog.action_type == "customer_warning_added",
        AuditLog.created_at >= week_ago
    ).count()
    
    recent_deregs = db.query(AuditLog).filter(
        AuditLog.action_type == "customer_deregistered",
        AuditLog.created_at >= week_ago
    ).count()
    
    # Pending items
    pending_complaints = db.query(Complaint).filter(
        Complaint.status == "pending",
        Complaint.type == "complaint"
    ).count()
    
    pending_disputes = db.query(Complaint).filter(
        Complaint.status == "disputed"
    ).count()
    
    pending_compliments = db.query(Complaint).filter(
        Complaint.status == "pending",
        Complaint.type == "compliment"
    ).count()
    
    return ReputationDashboardStats(
        total_employees=total_employees,
        active_employees=active_employees,
        demoted_employees=demoted_employees,
        fired_employees=fired_employees,
        employees_near_demotion=employees_near_demotion,
        employees_near_firing=employees_near_firing,
        employees_bonus_eligible=employees_bonus_eligible,
        total_customers=total_customers,
        vip_customers=vip_customers,
        customers_with_warnings=customers_with_warnings,
        customers_near_deregistration=customers_near_dereg,
        deregistered_customers=deregistered,
        recent_demotions=recent_demotions,
        recent_firings=recent_firings,
        recent_bonuses=recent_bonuses,
        recent_warnings_issued=recent_warnings,
        recent_deregistrations=recent_deregs,
        pending_complaints=pending_complaints,
        pending_disputes=pending_disputes,
        pending_compliments=pending_compliments
    )


@router.get("/reputation/employees", response_model=EmployeeListWithReputationResponse)
async def get_employees_with_reputation(
    type_filter: Optional[str] = Query(None, description="Filter by: chef, delivery"),
    status_filter: Optional[str] = Query(None, description="Filter by: active, demoted, fired"),
    at_risk_only: bool = Query(False, description="Only show at-risk employees"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Get all employees with full reputation data.
    """
    query = db.query(Account).filter(Account.type.in_(["chef", "delivery"]))
    
    if type_filter:
        query = query.filter(Account.type == type_filter)
    
    if status_filter:
        if status_filter == "fired":
            query = query.filter(Account.is_fired == True)
        else:
            query = query.filter(
                Account.is_fired == False,
                Account.employment_status == status_filter
            )
    
    if at_risk_only:
        query = query.filter(
            ((Account.complaint_count >= 2) | 
             (Account.rolling_avg_rating < 2.5) |
             (Account.times_demoted >= 1)),
            Account.is_fired == False
        )
    
    total = query.count()
    employees = query.order_by(Account.ID.desc()).offset(offset).limit(limit).all()
    
    results = []
    for emp in employees:
        summary = rep_engine.get_employee_reputation_summary(db, emp)
        
        # Build status warning message
        status_warning = None
        if summary["near_firing"]:
            status_warning = "One more demotion will result in termination"
        elif summary["near_demotion"]:
            status_warning = "At risk of demotion due to low rating or complaints"
        
        results.append(EmployeeReputationSummary(
            employee_id=summary["employee_id"],
            email=summary["email"],
            type=summary["type"],
            employment_status=summary["employment_status"],
            rolling_avg_rating=summary["rolling_avg_rating"],
            total_rating_count=summary["total_rating_count"],
            complaint_count=summary["complaint_count"],
            compliment_count=summary["compliment_count"],
            demotion_count=summary["demotion_count"],
            bonus_count=summary["bonus_count"],
            is_fired=summary["is_fired"],
            wage_cents=summary["wage"],
            near_demotion=summary["near_demotion"],
            near_firing=summary["near_firing"],
            bonus_eligible=summary["bonus_eligible"],
            status_warning=status_warning
        ))
    
    # Counts
    chefs_count = sum(1 for e in results if e.type == "chef")
    delivery_count = sum(1 for e in results if e.type == "delivery")
    at_risk_count = sum(1 for e in results if e.near_demotion or e.near_firing)
    bonus_eligible_count = sum(1 for e in results if e.bonus_eligible)
    
    return EmployeeListWithReputationResponse(
        employees=results,
        total=total,
        chefs_count=chefs_count,
        delivery_count=delivery_count,
        at_risk_count=at_risk_count,
        bonus_eligible_count=bonus_eligible_count
    )


@router.get("/reputation/employees/{employee_id}", response_model=EmployeeReputationSummary)
async def get_employee_reputation(
    employee_id: int,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get reputation summary for a specific employee.
    Employees can view their own, managers can view any.
    """
    employee = db.query(Account).filter(
        Account.ID == employee_id,
        Account.type.in_(["chef", "delivery"])
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Check permissions
    if current_user.type != "manager" and current_user.ID != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own reputation"
        )
    
    summary = rep_engine.get_employee_reputation_summary(db, employee)
    
    status_warning = None
    if summary["near_firing"]:
        status_warning = "One more demotion will result in termination"
    elif summary["near_demotion"]:
        status_warning = "At risk of demotion due to low rating or complaints"
    
    return EmployeeReputationSummary(
        employee_id=summary["employee_id"],
        email=summary["email"],
        type=summary["type"],
        employment_status=summary["employment_status"],
        rolling_avg_rating=summary["rolling_avg_rating"],
        total_rating_count=summary["total_rating_count"],
        complaint_count=summary["complaint_count"],
        compliment_count=summary["compliment_count"],
        demotion_count=summary["demotion_count"],
        bonus_count=summary["bonus_count"],
        is_fired=summary["is_fired"],
        wage_cents=summary["wage"],
        near_demotion=summary["near_demotion"],
        near_firing=summary["near_firing"],
        bonus_eligible=summary["bonus_eligible"],
        status_warning=status_warning
    )


@router.get("/reputation/customers", response_model=CustomerListWithWarningsResponse)
async def get_customers_with_warnings(
    tier_filter: Optional[str] = Query(None, description="Filter by: registered, vip, deregistered"),
    at_risk_only: bool = Query(False, description="Only show at-risk customers"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Get all customers with warning data.
    """
    query = db.query(Account).filter(Account.type.in_(["customer", "vip", "visitor", "deregistered"]))
    
    if tier_filter:
        if tier_filter == "vip":
            query = query.filter(Account.type == "vip")
        elif tier_filter == "deregistered":
            query = query.filter(Account.is_blacklisted == True)
        else:
            query = query.filter(Account.type.in_(["customer", "visitor"]))
    
    if at_risk_only:
        query = query.filter(
            Account.warnings >= 2,
            Account.is_blacklisted == False
        )
    
    total = query.count()
    customers = query.order_by(Account.warnings.desc(), Account.ID.desc()).offset(offset).limit(limit).all()
    
    results = []
    for cust in customers:
        summary = rep_engine.get_customer_warning_summary(db, cust)
        
        # Check for active disputes
        has_dispute = db.query(Complaint).filter(
            Complaint.accountID == cust.ID,
            Complaint.status == "disputed"
        ).first() is not None
        
        results.append(CustomerWarningSummary(
            customer_id=summary["customer_id"],
            email=summary["email"],
            type=summary["type"],
            customer_tier=summary["customer_tier"],
            warning_count=summary["warning_count"],
            threshold=summary["threshold"],
            is_blacklisted=summary["is_blacklisted"],
            near_threshold=summary["near_threshold"],
            has_active_dispute=has_dispute,
            warning_message=summary["warning_message"]
        ))
    
    vip_count = sum(1 for c in results if c.type == "vip")
    at_risk_count = sum(1 for c in results if c.near_threshold)
    dereg_count = sum(1 for c in results if c.is_blacklisted)
    
    return CustomerListWithWarningsResponse(
        customers=results,
        total=total,
        vip_count=vip_count,
        at_risk_count=at_risk_count,
        deregistered_count=dereg_count
    )


@router.get("/reputation/my-warnings", response_model=CustomerWarningSummary)
async def get_my_warnings(
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get warning summary for the current customer.
    Shows warning count, tier, and any alert messages.
    """
    if current_user.type not in ["customer", "vip", "visitor"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is for customers only"
        )
    
    summary = rep_engine.get_customer_warning_summary(db, current_user)
    
    # Check for active disputes
    has_dispute = db.query(Complaint).filter(
        Complaint.accountID == current_user.ID,
        Complaint.status == "disputed"
    ).first() is not None
    
    return CustomerWarningSummary(
        customer_id=summary["customer_id"],
        email=summary["email"],
        type=summary["type"],
        customer_tier=summary["customer_tier"],
        warning_count=summary["warning_count"],
        threshold=summary["threshold"],
        is_blacklisted=summary["is_blacklisted"],
        near_threshold=summary["near_threshold"],
        has_active_dispute=has_dispute,
        warning_message=summary["warning_message"]
    )


@router.get("/reputation/my-status", response_model=EmployeeReputationSummary)
async def get_my_employee_status(
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get reputation status for the current employee (chef or delivery).
    Shows all reputation metrics and any warnings.
    """
    if current_user.type not in ["chef", "delivery"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is for employees only"
        )
    
    summary = rep_engine.get_employee_reputation_summary(db, current_user)
    
    status_warning = None
    if summary["near_firing"]:
        status_warning = "⚠️ Warning: One more demotion will result in termination"
    elif summary["near_demotion"]:
        status_warning = "⚠️ Warning: You are at risk of demotion"
    elif summary["bonus_eligible"]:
        status_warning = "🌟 Great work! You're eligible for a bonus"
    
    return EmployeeReputationSummary(
        employee_id=summary["employee_id"],
        email=summary["email"],
        type=summary["type"],
        employment_status=summary["employment_status"],
        rolling_avg_rating=summary["rolling_avg_rating"],
        total_rating_count=summary["total_rating_count"],
        complaint_count=summary["complaint_count"],
        compliment_count=summary["compliment_count"],
        demotion_count=summary["demotion_count"],
        bonus_count=summary["bonus_count"],
        is_fired=summary["is_fired"],
        wage_cents=summary["wage"],
        near_demotion=summary["near_demotion"],
        near_firing=summary["near_firing"],
        bonus_eligible=summary["bonus_eligible"],
        status_warning=status_warning
    )


@router.post("/reputation/evaluate-all")
async def evaluate_all_reputation(
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Run reputation evaluation for all employees.
    Checks all rules and applies demotions, firings, and bonuses as needed.
    """
    results = rep_engine.run_all_employee_evaluations(db, current_user.ID)
    db.commit()
    
    demoted = sum(1 for r in results if r.get("demoted"))
    fired = sum(1 for r in results if r.get("fired"))
    bonuses = sum(1 for r in results if r.get("bonus_awarded"))
    
    return {
        "message": f"Evaluated {len(results)} employees",
        "summary": {
            "total_evaluated": len(results),
            "demotions": demoted,
            "firings": fired,
            "bonuses_awarded": bonuses
        },
        "details": results
    }
