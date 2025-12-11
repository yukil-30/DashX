"""
Manager Router
Handles manager-specific functionality:
- Employee Management (Create/Promote/Demote/Fire chefs and delivery)
- Dispute Resolution
- Bidding Decisions
- Dashboard Statistics
- KB Moderation

Business Rules:
- Chef/Delivery demoted after: avg rating < 2 OR 3 complaints
- Fired after 2 demotions
- Bonus after high ratings (>4 avg) or 3 compliments
- Compliment cancels one complaint
- Manager decides final complaint/dispute resolutions
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from app.database import get_db
from app.models import (
    Account, Restaurant, Complaint, AuditLog, Blacklist, ManagerNotification, 
    Dish, Order, Bid, DeliveryRating, KnowledgeBase, ChatLog, VIPHistory
)
from app.schemas import (
    DeliveryPersonStats, KnowledgeBaseEntry
)
from app.auth import get_current_user, require_manager, hash_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manager", tags=["Manager"])


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


# ============================================================
# Pydantic Schemas for Manager Endpoints
# ============================================================

from pydantic import BaseModel, EmailStr, Field


class EmployeeCreateRequest(BaseModel):
    """Request to create a new employee account"""
    email: EmailStr = Field(..., description="Employee email")
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(..., description="Employee role: 'chef' or 'delivery'")
    wage_cents: Optional[int] = Field(None, description="Hourly wage in cents")


class EmployeeCreateResponse(BaseModel):
    """Response after creating employee"""
    message: str
    employee_id: int
    email: str
    role: str
    restaurant_id: int
    wage_cents: Optional[int] = None


class EmployeeResponse(BaseModel):
    """Employee details response"""
    id: int
    email: str
    type: str
    wage: Optional[int] = None
    warnings: int = 0
    times_demoted: int = 0
    is_fired: bool = False
    restaurant_id: Optional[int] = None
    # Stats
    total_complaints: int = 0
    total_compliments: int = 0
    average_rating: Optional[float] = None
    total_reviews: int = 0


class EmployeeListResponse(BaseModel):
    """List of employees"""
    employees: List[EmployeeResponse]
    total: int
    chefs_count: int
    delivery_count: int


class EmployeeActionRequest(BaseModel):
    """Request for employee action (promote/demote/fire)"""
    action: str = Field(..., description="Action: 'promote', 'demote', 'fire', 'bonus'")
    reason: Optional[str] = Field(None, max_length=500)
    amount_cents: Optional[int] = Field(None, description="Bonus/wage change amount in cents")


class EmployeeActionResponse(BaseModel):
    """Response after employee action"""
    message: str
    employee_id: int
    action: str
    previous_wage: Optional[int] = None
    new_wage: Optional[int] = None
    times_demoted: int = 0
    is_fired: bool = False
    audit_log_id: int


class DisputeResponse(BaseModel):
    """Dispute details for manager view"""
    complaint_id: int
    complaint_type: str
    description: str
    filer_id: int
    filer_email: str
    about_id: Optional[int] = None
    about_email: Optional[str] = None
    about_type: Optional[str] = None
    order_id: Optional[int] = None
    status: str
    is_disputed: bool = False
    dispute_reason: Optional[str] = None
    filer_warnings: int = 0
    about_warnings: int = 0
    about_complaints_count: int = 0
    about_compliments_count: int = 0
    created_at: Optional[str] = None


class DisputeListResponse(BaseModel):
    """List of disputes for manager"""
    disputes: List[DisputeResponse]
    total: int
    pending_count: int


class DisputeResolveRequest(BaseModel):
    """Request to resolve a dispute"""
    resolution: str = Field(..., description="'uphold' or 'dismiss'")
    notes: Optional[str] = Field(None, max_length=1000)


class DisputeResolveResponse(BaseModel):
    """Response after resolving dispute"""
    message: str
    complaint_id: int
    resolution: str
    warning_applied_to: Optional[int] = None
    new_warning_count: Optional[int] = None
    vip_downgrade: bool = False
    blacklisted: bool = False
    employee_demoted: bool = False
    employee_fired: bool = False
    audit_log_id: int


class DashboardStatsResponse(BaseModel):
    """Manager dashboard statistics"""
    # Pending items
    pending_complaints: int = 0
    pending_disputes: int = 0
    orders_awaiting_assignment: int = 0
    flagged_kb_items: int = 0
    unread_notifications: int = 0
    blocked_registration_attempts: int = 0
    # Employee stats
    total_employees: int = 0
    chefs_count: int = 0
    delivery_count: int = 0
    employees_at_risk: int = 0  # Near demotion/firing threshold
    # Restaurant stats
    restaurant_id: Optional[int] = None
    restaurant_name: Optional[str] = None
    total_orders: int = 0
    orders_today: int = 0
    revenue_today_cents: int = 0
    total_customers: int = 0
    total_vips: int = 0


class BiddingOrderResponse(BaseModel):
    """Order awaiting bid assignment"""
    order_id: int
    customer_email: str
    order_total: int
    delivery_address: str
    created_at: str
    bids_count: int
    lowest_bid_amount: Optional[int] = None
    lowest_bid_delivery_id: Optional[int] = None


class BiddingOrderListResponse(BaseModel):
    """List of orders awaiting bid assignment"""
    orders: List[BiddingOrderResponse]
    total: int


class AccountSummary(BaseModel):
    id: int
    email: str
    type: str
    warnings: int
    is_blacklisted: bool
    customer_tier: Optional[str] = None
    balance: int
    has_pending_deregister: bool = False


class CloseAccountRequest(BaseModel):
    reason: Optional[str] = None


class CloseAccountResponse(BaseModel):
    message: str
    account_id: int
    closed: bool


class BlacklistCreateRequest(BaseModel):
    email: EmailStr
    reason: Optional[str] = None
    original_account_id: Optional[int] = None


class BlacklistCreateResponse(BaseModel):
    message: str
    blacklist_id: int
    email: str


class BlacklistAttemptItem(BaseModel):
    id: int
    title: str
    message: str
    related_account_id: Optional[int] = None
    created_at: Optional[str] = None


class BlacklistAttemptListResponse(BaseModel):
    attempts: List[BlacklistAttemptItem]
    total: int


class BidAssignRequest(BaseModel):
    """Request to assign a bid to an order"""
    bid_id: int = Field(..., description="ID of the bid to accept")
    memo: Optional[str] = Field(None, max_length=500, description="Required if not lowest bid")


class BidAssignResponse(BaseModel):
    """Response after assigning bid"""
    message: str
    order_id: int
    bid_id: int
    delivery_person_id: int
    delivery_fee: int
    is_lowest_bid: bool
    memo_required: bool
    memo_saved: bool


class KBModerationResponse(BaseModel):
    """KB entry for moderation"""
    id: int
    question: str
    answer: str
    keywords: Optional[str] = None
    confidence: float
    author_id: Optional[int] = None
    author_email: Optional[str] = None
    is_active: bool
    flagged_count: int = 0
    avg_rating: Optional[float] = None
    created_at: Optional[str] = None


class KBModerationListResponse(BaseModel):
    """List of KB entries for moderation"""
    entries: List[KBModerationResponse]
    total: int
    flagged_count: int


# ============================================================
# Dashboard Endpoint
# ============================================================

@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard(
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Get manager dashboard with statistics and pending items.
    """
    # Get restaurant info
    restaurant = None
    if current_user.restaurantID:
        restaurant = db.query(Restaurant).filter(Restaurant.id == current_user.restaurantID).first()
    
    # Pending complaints
    pending_complaints = db.query(Complaint).filter(
        Complaint.status == "pending",
        Complaint.type == "complaint"
    ).count()
    
    # Pending disputes (complaints that have been disputed)
    pending_disputes = db.query(Complaint).filter(
        Complaint.status == "disputed"
    ).count()
    
    # Orders awaiting assignment (status = 'paid' with bids but no assigned bid)
    orders_awaiting = db.query(Order).filter(
        Order.status == "paid",
        Order.bidID == None
    ).join(Bid, Bid.orderID == Order.id).distinct().count()
    
    # Flagged KB items
    flagged_kb = db.query(ChatLog).filter(
        ChatLog.flagged == True,
        ChatLog.reviewed == False
    ).count()
    
    # Unread notifications
    unread_notifs = db.query(ManagerNotification).filter(
        ManagerNotification.is_read == False
    ).count()

    # Blocked registration attempts today (manager-visible activity)
    try:
        blocked_count = db.query(ManagerNotification).filter(
            ManagerNotification.notification_type == "blacklist_registration_attempt",
            ManagerNotification.created_at >= today_start
        ).count()
    except Exception:
        blocked_count = 0
    
    # Employee counts
    employees = db.query(Account).filter(
        Account.type.in_(["chef", "delivery"]),
        Account.is_fired == False
    )
    if current_user.restaurantID:
        employees = employees.filter(Account.restaurantID == current_user.restaurantID)
    
    total_employees = employees.count()
    chefs_count = employees.filter(Account.type == "chef").count()
    delivery_count = employees.filter(Account.type == "delivery").count()
    
    # Employees at risk (near threshold)
    employees_at_risk = db.query(Account).filter(
        Account.type.in_(["chef", "delivery"]),
        Account.is_fired == False,
        Account.times_demoted >= 1
    ).count()
    
    # Order stats
    total_orders = db.query(Order).count()
    
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    orders_today = db.query(Order).filter(Order.dateTime >= today_start).count()
    
    revenue_result = db.query(func.sum(Order.finalCost)).filter(
        Order.dateTime >= today_start,
        Order.status.in_(["paid", "assigned", "delivered"])
    ).scalar()
    revenue_today = revenue_result or 0
    
    # Customer counts
    total_customers = db.query(Account).filter(Account.type == "customer").count()
    total_vips = db.query(Account).filter(Account.type == "vip").count()
    
    return DashboardStatsResponse(
        pending_complaints=pending_complaints,
        pending_disputes=pending_disputes,
        orders_awaiting_assignment=orders_awaiting,
        flagged_kb_items=flagged_kb,
        unread_notifications=unread_notifs,
        blocked_registration_attempts=blocked_count,
        total_employees=total_employees,
        chefs_count=chefs_count,
        delivery_count=delivery_count,
        employees_at_risk=employees_at_risk,
        restaurant_id=restaurant.id if restaurant else None,
        restaurant_name=restaurant.name if restaurant else None,
        total_orders=total_orders,
        orders_today=orders_today,
        revenue_today_cents=revenue_today,
        total_customers=total_customers,
        total_vips=total_vips
    )


# ============================================================
# Account / Registration Management
# ============================================================


@router.get("/accounts", response_model=List[AccountSummary])
async def list_accounts(
    pending_only: bool = Query(False, description="Show only pending registrations"),
    role: Optional[str] = Query(None, description="Filter by role/type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    show_blacklisted: bool = Query(False, description="Include blacklisted accounts in results"),
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """List accounts needing manager action: pending registrations, deregister requests, blacklisted accounts, and accounts with warnings."""
    # First, get all accounts with pending deregister requests
    deregister_account_ids = db.query(ManagerNotification.related_account_id).filter(
        ManagerNotification.notification_type == 'deregister_request'
    ).all()
    deregister_ids_set = set(row[0] for row in deregister_account_ids if row[0])
    
    query = db.query(Account)
    if role:
        query = query.filter(Account.type == role)

    # Default: show accounts that need manager attention (pending, blacklisted, with deregister request, or with warnings)
    if pending_only:
        query = query.filter(Account.customer_tier == 'pending')
    else:
        deregister_ids_list = list(deregister_ids_set) if deregister_ids_set else []
        conditions = [
            Account.customer_tier == 'pending',
            (Account.type == 'customer') & (Account.warnings > 0)
        ]
        # Only include blacklisted accounts if explicitly requested
        if show_blacklisted:
            conditions.insert(1, Account.is_blacklisted == True)

        if deregister_ids_list:
            conditions.append(Account.ID.in_(deregister_ids_list))

        query = query.filter(or_(*conditions))

    accounts = query.order_by(Account.ID.desc()).offset(offset).limit(limit).all()
    
    # Filter out accounts that are already deregistered (closed) and do not need manager action.
    # Keep accounts that are blacklisted or have pending deregister requests so managers can still see them.
    results = []
    for a in accounts:
        # Skip if account is deregistered and not blacklisted and has no pending deregister request
        if getattr(a, 'customer_tier', None) == 'deregistered' and not a.is_blacklisted and a.ID not in deregister_ids_set:
            continue
        results.append(AccountSummary(
            id=a.ID,
            email=a.email,
            type=a.type,
            warnings=a.warnings,
            is_blacklisted=bool(a.is_blacklisted),
            customer_tier=getattr(a, 'customer_tier', None),
            balance=getattr(a, 'balance', 0),
            has_pending_deregister=a.ID in deregister_ids_set
        ))

    return results


@router.post("/accounts/{account_id}/approve", response_model=dict)
async def approve_registration(
    account_id: int,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Approve a pending customer registration."""
    account = db.query(Account).filter(Account.ID == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    
    if account.customer_tier != 'pending':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is not pending approval")
    
    account.customer_tier = 'registered'
    
    now_iso = datetime.now(timezone.utc).isoformat()
    create_audit_entry(
        db,
        action_type="registration_approved",
        actor_id=current_user.ID,
        target_id=account.ID,
        details={},
    )
    
    create_manager_notification(
        db,
        notification_type="registration_approved",
        title="Registration Approved",
        message=f"Registration for {account.email} has been approved",
        related_account_id=account.ID,
    )
    
    db.commit()
    return {"message": "Registration approved", "account_id": account_id}


@router.post("/accounts/{account_id}/reject", response_model=dict)
async def reject_registration(
    account_id: int,
    reason: Optional[str] = None,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Reject a pending customer registration and add to blacklist."""
    account = db.query(Account).filter(Account.ID == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    
    if account.customer_tier != 'pending':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is not pending approval")
    
    now_iso = datetime.now(timezone.utc).isoformat()
    blacklist_entry = Blacklist(
        email=account.email,
        reason=reason or "Registration rejected by manager",
        original_account_id=account.ID,
        blacklisted_by=current_user.ID,
        created_at=now_iso
    )
    db.add(blacklist_entry)
    
    account.is_blacklisted = True
    account.customer_tier = 'deregistered'
    
    create_audit_entry(
        db,
        action_type="registration_rejected",
        actor_id=current_user.ID,
        target_id=account.ID,
        details={"reason": reason},
    )
    
    create_manager_notification(
        db,
        notification_type="registration_rejected",
        title="Registration Rejected",
        message=f"Registration for {account.email} was rejected",
        related_account_id=account.ID,
    )
    
    db.commit()
    return {"message": "Registration rejected and blacklisted", "account_id": account_id}


@router.post("/accounts/{account_id}/close", response_model=CloseAccountResponse)
async def close_account(
    account_id: int,
    request: CloseAccountRequest,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Close / deregister an account. Marks customer_tier as 'deregistered'. Does NOT blacklist (closing ≠ blacklisting)."""
    account = db.query(Account).filter(Account.ID == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    # Apply closure: record previous state, zero balance, mark as deregistered
    # NOTE: Closing an account is NOT the same as blacklisting. Blacklisting is for violations/rejection.
    previous = {
        "type": account.type,
        "customer_tier": getattr(account, 'customer_tier', None),
        "is_blacklisted": account.is_blacklisted
    }

    account.balance = 0
    account.customer_tier = 'deregistered'
    # Do NOT set is_blacklisted to True on close - that's only for rejection/violations
    account.type = 'visitor'

    # Create audit and manager notification
    now_iso = datetime.now(timezone.utc).isoformat()
    audit = create_audit_entry(
        db,
        action_type="account_closed",
        actor_id=current_user.ID,
        target_id=account.ID,
        details={"reason": request.reason, "previous": previous},
    )

    create_manager_notification(
        db,
        notification_type="account_closed",
        title="Account Closed",
        message=f"Account {account.email} closed by {current_user.email}. Reason: {request.reason or 'No reason provided'}",
        related_account_id=account.ID,
        related_order_id=None
    )

    db.commit()

    return CloseAccountResponse(message="Account closed/deregistered", account_id=account.ID, closed=True)


@router.post("/accounts/{account_id}/close-deregister", response_model=dict)
async def close_deregister_request(
    account_id: int,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Close/approve a pending deregister request from a customer. Sets customer_tier='deregistered'."""
    account = db.query(Account).filter(Account.ID == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    
    # Check if account already deregistered
    if account.customer_tier == 'deregistered':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is already deregistered"
        )
    
    # Remove any pending deregister notifications for this account
    pending_notifs_q = db.query(ManagerNotification).filter(
        ManagerNotification.notification_type == "deregister_request",
        ManagerNotification.related_account_id == account_id
    )
    pending_count = pending_notifs_q.count()
    if pending_count == 0:
        logger.warning(f"No pending deregister notification for account {account_id}, but proceeding with closure")
    else:
        # Delete all pending deregister notifications for this account
        pending_notifs_q.delete(synchronize_session=False)
        logger.info(f"Deleted {pending_count} pending deregister notification(s) for account {account_id}")
    
    # Record original email for audit, then anonymize to allow re-registration
    original_email = account.email

    # Set account as deregistered
    account.customer_tier = 'deregistered'
    account.balance = 0
    account.type = 'visitor'
    # Do NOT blacklist - close is not blacklist

    # Anonymize email so the same address can be reused by a new registration
    try:
        anon_email = f"deregistered+{account.ID}@example.invalid"
    except Exception:
        anon_email = f"deregistered+{int(datetime.now(timezone.utc).timestamp())}@example.invalid"
    account.email = anon_email
    # Clear password so this account cannot be used to login even if email reused
    account.password = ""
    
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Create audit log (include original email for traceability)
    audit = create_audit_entry(
        db,
        action_type="deregister_approved",
        actor_id=current_user.ID,
        target_id=account.ID,
        details={"reason": "Customer deregister request approved", "original_email": original_email},
    )
    
    # Create manager notification about the closure
    create_manager_notification(
        db,
        notification_type="deregister_approved",
        title="Deregister Request Approved",
        message=f"Account {account.email} has been deregistered and closed",
        related_account_id=account.ID,
    )
    
    db.commit()
    logger.info(f"Account {account_id} deregistered by manager {current_user.ID}")
    
    return {"message": "Account deregistered and closed successfully", "account_id": account_id}


@router.post("/blacklist", response_model=BlacklistCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_blacklist_entry(
    request: BlacklistCreateRequest,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Manually add an email to the global blacklist."""
    existing = db.query(Blacklist).filter(Blacklist.email == request.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already blacklisted")

    now_iso = datetime.now(timezone.utc).isoformat()
    entry = Blacklist(
        email=request.email,
        reason=request.reason,
        original_account_id=request.original_account_id,
        blacklisted_by=current_user.ID,
        created_at=now_iso
    )
    db.add(entry)

    # Audit and notification
    create_audit_entry(
        db,
        action_type="blacklist_added",
        actor_id=current_user.ID,
        target_id=request.original_account_id,
        details={"email": request.email, "reason": request.reason},
    )

    create_manager_notification(
        db,
        notification_type="blacklist_added",
        title="Blacklist Entry Added",
        message=f"{request.email} was added to blacklist by {current_user.email}",
        related_account_id=request.original_account_id,
        related_order_id=None
    )

    db.commit()
    db.refresh(entry)

    return BlacklistCreateResponse(message="Email blacklisted", blacklist_id=entry.id, email=entry.email)


@router.get("/blacklist-attempts", response_model=BlacklistAttemptListResponse)
async def get_blacklist_attempts(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """List manager notifications representing blocked registration attempts."""
    q = db.query(ManagerNotification).filter(ManagerNotification.notification_type == "blacklist_registration_attempt")
    total = q.count()
    items = q.order_by(ManagerNotification.created_at.desc()).offset(offset).limit(limit).all()

    attempts = []
    for it in items:
        attempts.append(BlacklistAttemptItem(
            id=it.id,
            title=it.title,
            message=it.message,
            related_account_id=it.related_account_id,
            created_at=it.created_at
        ))

    return BlacklistAttemptListResponse(attempts=attempts, total=total)


# ============================================================
# Employee Management Endpoints
# ============================================================

@router.post("/employees", response_model=EmployeeCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    request: EmployeeCreateRequest,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Create a new employee account (chef or delivery).
    Manager must be associated with a restaurant.
    """
    # Validate role
    if request.role not in ["chef", "delivery"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'chef' or 'delivery'"
        )
    
    # Validate manager has a restaurant
    if not current_user.restaurantID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manager must be associated with a restaurant to create employees"
        )
    
    # Check if email already exists
    existing = db.query(Account).filter(Account.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create employee account
    employee = Account(
        email=request.email,
        password=hash_password(request.password),
        type=request.role,
        restaurantID=current_user.restaurantID,
        wage=request.wage_cents,
        balance=0,
        warnings=0,
        times_demoted=0,
        is_fired=False
    )
    db.add(employee)
    db.flush()
    
    # Create delivery rating record for delivery personnel
    if request.role == "delivery":
        delivery_rating = DeliveryRating(
            accountID=employee.ID,
            averageRating=Decimal("0.00"),
            reviews=0,
            total_deliveries=0,
            on_time_deliveries=0,
            avg_delivery_minutes=30
        )
        db.add(delivery_rating)
    
    # Create audit entry
    create_audit_entry(
        db,
        action_type="employee_created",
        actor_id=current_user.ID,
        target_id=employee.ID,
        details={
            "role": request.role,
            "restaurant_id": current_user.restaurantID,
            "wage": request.wage_cents
        }
    )
    
    db.commit()
    db.refresh(employee)
    
    logger.info(f"Employee {employee.email} ({request.role}) created by manager {current_user.email}")
    
    return EmployeeCreateResponse(
        message=f"{request.role.capitalize()} account created successfully",
        employee_id=employee.ID,
        email=employee.email,
        role=employee.type,
        restaurant_id=employee.restaurantID,
        wage_cents=employee.wage
    )


@router.get("/employees", response_model=EmployeeListResponse)
async def list_employees(
    role_filter: Optional[str] = Query(None, description="Filter by role: chef, delivery"),
    include_fired: bool = Query(False, description="Include fired employees"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    List all employees for the manager's restaurant.
    """
    query = db.query(Account).filter(Account.type.in_(["chef", "delivery"]))
    
    # Filter by manager's restaurant
    if current_user.restaurantID:
        query = query.filter(Account.restaurantID == current_user.restaurantID)
    
    if role_filter:
        query = query.filter(Account.type == role_filter)
    
    if not include_fired:
        query = query.filter(Account.is_fired == False)
    
    total = query.count()
    employees = query.order_by(Account.ID.desc()).offset(offset).limit(limit).all()
    
    # Build response with stats
    results = []
    for emp in employees:
        # Count complaints/compliments
        complaints_count = db.query(Complaint).filter(
            Complaint.accountID == emp.ID,
            Complaint.type == "complaint",
            Complaint.status == "resolved",
            Complaint.resolution == "warning_issued"
        ).count()
        
        compliments_count = db.query(Complaint).filter(
            Complaint.accountID == emp.ID,
            Complaint.type == "compliment"
        ).count()
        
        # Get rating based on role
        avg_rating = None
        total_reviews = 0
        
        if emp.type == "chef":
            rating_result = db.query(
                func.avg(Dish.average_rating),
                func.sum(Dish.reviews)
            ).filter(
                Dish.chefID == emp.ID,
                Dish.reviews > 0
            ).first()
            if rating_result[0]:
                avg_rating = float(rating_result[0])
                total_reviews = int(rating_result[1] or 0)
        else:  # delivery
            delivery_rating = db.query(DeliveryRating).filter(
                DeliveryRating.accountID == emp.ID
            ).first()
            if delivery_rating:
                avg_rating = float(delivery_rating.averageRating) if delivery_rating.averageRating else None
                total_reviews = delivery_rating.reviews
        
        results.append(EmployeeResponse(
            id=emp.ID,
            email=emp.email,
            type=emp.type,
            wage=emp.wage,
            warnings=emp.warnings,
            times_demoted=emp.times_demoted,
            is_fired=emp.is_fired,
            restaurant_id=emp.restaurantID,
            total_complaints=complaints_count,
            total_compliments=compliments_count,
            average_rating=avg_rating,
            total_reviews=total_reviews
        ))
    
    # Count by role
    chefs = sum(1 for e in results if e.type == "chef")
    delivery = sum(1 for e in results if e.type == "delivery")
    
    return EmployeeListResponse(
        employees=results,
        total=total,
        chefs_count=chefs,
        delivery_count=delivery
    )


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Get details for a specific employee."""
    employee = db.query(Account).filter(
        Account.ID == employee_id,
        Account.type.in_(["chef", "delivery"])
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Count complaints/compliments
    complaints_count = db.query(Complaint).filter(
        Complaint.accountID == employee.ID,
        Complaint.type == "complaint",
        Complaint.status == "resolved",
        Complaint.resolution == "warning_issued"
    ).count()
    
    compliments_count = db.query(Complaint).filter(
        Complaint.accountID == employee.ID,
        Complaint.type == "compliment"
    ).count()
    
    # Get rating
    avg_rating = None
    total_reviews = 0
    
    if employee.type == "chef":
        rating_result = db.query(
            func.avg(Dish.average_rating),
            func.sum(Dish.reviews)
        ).filter(
            Dish.chefID == employee.ID,
            Dish.reviews > 0
        ).first()
        if rating_result[0]:
            avg_rating = float(rating_result[0])
            total_reviews = int(rating_result[1] or 0)
    else:
        delivery_rating = db.query(DeliveryRating).filter(
            DeliveryRating.accountID == employee.ID
        ).first()
        if delivery_rating:
            avg_rating = float(delivery_rating.averageRating) if delivery_rating.averageRating else None
            total_reviews = delivery_rating.reviews
    
    return EmployeeResponse(
        id=employee.ID,
        email=employee.email,
        type=employee.type,
        wage=employee.wage,
        warnings=employee.warnings,
        times_demoted=employee.times_demoted,
        is_fired=employee.is_fired,
        restaurant_id=employee.restaurantID,
        total_complaints=complaints_count,
        total_compliments=compliments_count,
        average_rating=avg_rating,
        total_reviews=total_reviews
    )


@router.post("/employees/{employee_id}/action", response_model=EmployeeActionResponse)
async def employee_action(
    employee_id: int,
    request: EmployeeActionRequest,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Perform an action on an employee: promote, demote, fire, or bonus.
    
    Actions:
    - promote: Increase wage by 10%
    - demote: Decrease wage by 10%, increment times_demoted
    - fire: Mark as fired
    - bonus: Add one-time bonus to balance
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
    
    if employee.is_fired and request.action != "promote":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot perform actions on fired employees (except re-hire via promote)"
        )
    
    previous_wage = employee.wage
    new_wage = employee.wage
    
    if request.action == "promote":
        # Increase wage by 10%
        if employee.wage:
            new_wage = int(employee.wage * 1.1)
            employee.wage = new_wage
        
        # Re-hire if was fired
        if employee.is_fired:
            employee.is_fired = False
            employee.times_demoted = 0
        
        logger.info(f"Employee {employee.email} promoted by {current_user.email}")
    
    elif request.action == "demote":
        employee.times_demoted += 1
        
        # Check if should be fired (2 demotions)
        if employee.times_demoted >= 2:
            employee.is_fired = True
            employee.previous_type = employee.type
            logger.info(f"Employee {employee.email} fired after 2 demotions")
        else:
            # Reduce wage by 10%
            if employee.wage:
                new_wage = int(employee.wage * 0.9)
                employee.wage = new_wage
            logger.info(f"Employee {employee.email} demoted by {current_user.email}")
    
    elif request.action == "fire":
        employee.is_fired = True
        employee.previous_type = employee.type
        logger.info(f"Employee {employee.email} fired by {current_user.email}")
    
    elif request.action == "bonus":
        if not request.amount_cents or request.amount_cents <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bonus amount must be positive"
            )
        employee.balance = (employee.balance or 0) + request.amount_cents
        logger.info(f"Employee {employee.email} given bonus of {request.amount_cents} cents")
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be: promote, demote, fire, or bonus"
        )
    
    # Create audit entry
    audit_entry = create_audit_entry(
        db,
        action_type=f"employee_{request.action}",
        actor_id=current_user.ID,
        target_id=employee.ID,
        details={
            "action": request.action,
            "reason": request.reason,
            "previous_wage": previous_wage,
            "new_wage": new_wage,
            "times_demoted": employee.times_demoted,
            "is_fired": employee.is_fired,
            "bonus_amount": request.amount_cents if request.action == "bonus" else None
        }
    )
    
    db.commit()
    
    return EmployeeActionResponse(
        message=f"Employee {request.action} action completed",
        employee_id=employee.ID,
        action=request.action,
        previous_wage=previous_wage,
        new_wage=new_wage,
        times_demoted=employee.times_demoted,
        is_fired=employee.is_fired,
        audit_log_id=audit_entry.id
    )


# ============================================================
# HR Auto-Evaluation Endpoints
# ============================================================

@router.post("/employees/evaluate-all")
async def evaluate_all_employees(
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Evaluate all employees for automatic demotion/bonus rules:
    - Demote if: avg rating < 2 OR 3+ complaints
    - Bonus if: avg rating > 4 OR 3+ compliments
    - Fire if: 2 demotions
    """
    employees = db.query(Account).filter(
        Account.type.in_(["chef", "delivery"]),
        Account.is_fired == False
    ).all()
    
    results = []
    
    for emp in employees:
        # Count complaints with warning issued
        complaints_count = db.query(Complaint).filter(
            Complaint.accountID == emp.ID,
            Complaint.type == "complaint",
            Complaint.status == "resolved",
            Complaint.resolution == "warning_issued"
        ).count()
        
        # Count compliments
        compliments_count = db.query(Complaint).filter(
            Complaint.accountID == emp.ID,
            Complaint.type == "compliment"
        ).count()
        
        # Get average rating
        avg_rating = None
        if emp.type == "chef":
            rating_result = db.query(func.avg(Dish.average_rating)).filter(
                Dish.chefID == emp.ID,
                Dish.reviews > 0
            ).scalar()
            avg_rating = float(rating_result) if rating_result else None
        else:
            delivery_rating = db.query(DeliveryRating).filter(
                DeliveryRating.accountID == emp.ID
            ).first()
            if delivery_rating:
                avg_rating = float(delivery_rating.averageRating) if delivery_rating.averageRating else None
        
        action_taken = None
        
        # Check for demotion (low rating or 3+ complaints)
        should_demote = (avg_rating is not None and avg_rating < 2.0) or complaints_count >= 3
        
        # Check for bonus (high rating or 3+ compliments)
        should_bonus = (avg_rating is not None and avg_rating > 4.0) or compliments_count >= 3
        
        if should_demote:
            emp.times_demoted += 1
            if emp.times_demoted >= 2:
                emp.is_fired = True
                action_taken = "fired"
            else:
                if emp.wage:
                    emp.wage = int(emp.wage * 0.9)
                action_taken = "demoted"
            
            create_audit_entry(
                db,
                action_type=f"employee_{action_taken}_auto",
                actor_id=current_user.ID,
                target_id=emp.ID,
                details={
                    "avg_rating": avg_rating,
                    "complaints_count": complaints_count,
                    "times_demoted": emp.times_demoted
                }
            )
        
        elif should_bonus and not should_demote:
            # Give bonus of 10% of wage
            bonus_amount = int((emp.wage or 1500) * 0.1)
            emp.balance = (emp.balance or 0) + bonus_amount
            action_taken = f"bonus_{bonus_amount}"
            
            create_audit_entry(
                db,
                action_type="employee_bonus_auto",
                actor_id=current_user.ID,
                target_id=emp.ID,
                details={
                    "avg_rating": avg_rating,
                    "compliments_count": compliments_count,
                    "bonus_amount": bonus_amount
                }
            )
        
        results.append({
            "employee_id": emp.ID,
            "email": emp.email,
            "type": emp.type,
            "avg_rating": avg_rating,
            "complaints": complaints_count,
            "compliments": compliments_count,
            "action_taken": action_taken
        })
    
    db.commit()
    
    return {
        "message": f"Evaluated {len(employees)} employees",
        "results": results
    }


# ============================================================
# Dispute Resolution Endpoints
# ============================================================

@router.get("/disputes", response_model=DisputeListResponse)
async def list_disputes(
    status_filter: Optional[str] = Query(None, description="Filter: pending, disputed, resolved"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    List all disputes and complaints pending manager resolution.
    Shows complaint details, parties involved, and warning count impact.
    """
    query = db.query(Complaint)
    
    if status_filter:
        query = query.filter(Complaint.status == status_filter)
    else:
        # By default, show pending and disputed
        query = query.filter(Complaint.status.in_(["pending", "disputed"]))
    
    total = query.count()
    pending_count = db.query(Complaint).filter(Complaint.status.in_(["pending", "disputed"])).count()
    
    complaints = query.order_by(Complaint.created_at.desc()).offset(offset).limit(limit).all()
    
    results = []
    for c in complaints:
        filer = db.query(Account).filter(Account.ID == c.filer).first()
        about = db.query(Account).filter(Account.ID == c.accountID).first() if c.accountID else None
        
        # Count complaints/compliments for about user
        about_complaints = 0
        about_compliments = 0
        if about:
            about_complaints = db.query(Complaint).filter(
                Complaint.accountID == about.ID,
                Complaint.type == "complaint"
            ).count()
            about_compliments = db.query(Complaint).filter(
                Complaint.accountID == about.ID,
                Complaint.type == "compliment"
            ).count()
        
        # Check if disputed (we'll mark complaints filed by delivery as potential disputes)
        is_disputed = c.status == "disputed" or c.disputed
        
        results.append(DisputeResponse(
            complaint_id=c.id,
            complaint_type=c.type,
            description=c.description,
            filer_id=c.filer,
            filer_email=filer.email if filer else "Unknown",
            about_id=c.accountID,
            about_email=about.email if about else None,
            about_type=about.type if about else None,
            order_id=c.order_id,
            status=c.status,
            is_disputed=is_disputed,
            dispute_reason=c.dispute_reason,  # Include dispute reason from complaint
            filer_warnings=filer.warnings if filer else 0,
            about_warnings=about.warnings if about else 0,
            about_complaints_count=about_complaints,
            about_compliments_count=about_compliments,
            created_at=c.created_at.isoformat() if c.created_at else None
        ))
    
    return DisputeListResponse(
        disputes=results,
        total=total,
        pending_count=pending_count
    )


@router.post("/disputes/{complaint_id}/resolve", response_model=DisputeResolveResponse)
async def resolve_dispute(
    complaint_id: int,
    request: DisputeResolveRequest,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Resolve a dispute/complaint.
    
    Resolutions:
    - uphold: Complaint is valid -> target gets warning, check demotion/blacklist rules
    - dismiss: Complaint without merit -> filer gets warning
    
    Automatically applies:
    - VIP downgrades (2 warnings -> demote to customer)
    - Customer blacklisting (3 warnings -> blacklisted)
    - Employee demotion/firing rules
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
    
    # Update complaint
    complaint.status = "resolved"
    complaint.resolution = "warning_issued" if request.resolution == "uphold" else "dismissed"
    complaint.resolved_by = current_user.ID
    complaint.resolved_at = get_iso_now()
    
    warning_applied_to = None
    new_warning_count = None
    vip_downgrade = False
    blacklisted = False
    employee_demoted = False
    employee_fired = False
    
    if request.resolution == "uphold":
        # Valid complaint -> add warning to target
        if complaint.accountID:
            target = db.query(Account).filter(Account.ID == complaint.accountID).first()
            if target:
                target.warnings += 1
                warning_applied_to = target.ID
                new_warning_count = target.warnings
                
                # Apply customer/VIP rules
                if target.type == "vip" and target.warnings >= 2:
                    # VIP downgrade
                    target.previous_type = "vip"
                    target.type = "customer"
                    target.warnings = 0
                    vip_downgrade = True
                    
                    # Record VIP history
                    vip_record = VIPHistory(
                        account_id=target.ID,
                        previous_type="vip",
                        new_type="customer",
                        reason="2 warnings received",
                        changed_by=current_user.ID,
                        created_at=get_iso_now()
                    )
                    db.add(vip_record)
                
                elif target.type == "customer" and target.warnings >= 3:
                    # Blacklist
                    target.is_blacklisted = True
                    blacklisted = True
                    
                    blacklist_entry = Blacklist(
                        email=target.email,
                        reason="3 warnings received",
                        original_account_id=target.ID,
                        blacklisted_by=current_user.ID,
                        created_at=get_iso_now()
                    )
                    db.add(blacklist_entry)
                
                elif target.type in ["chef", "delivery"]:
                    # Check employee demotion rules
                    complaints_count = db.query(Complaint).filter(
                        Complaint.accountID == target.ID,
                        Complaint.type == "complaint",
                        Complaint.status == "resolved",
                        Complaint.resolution == "warning_issued"
                    ).count()
                    
                    if complaints_count >= 3:
                        target.times_demoted += 1
                        if target.times_demoted >= 2:
                            target.is_fired = True
                            employee_fired = True
                        else:
                            if target.wage:
                                target.wage = int(target.wage * 0.9)
                            employee_demoted = True
    
    else:  # dismiss
        # Complaint without merit -> add warning to filer
        filer = db.query(Account).filter(Account.ID == complaint.filer).first()
        if filer:
            filer.warnings += 1
            warning_applied_to = filer.ID
            new_warning_count = filer.warnings
            
            # Apply customer/VIP rules
            if filer.type == "vip" and filer.warnings >= 2:
                filer.previous_type = "vip"
                filer.type = "customer"
                filer.warnings = 0
                vip_downgrade = True
                
                vip_record = VIPHistory(
                    account_id=filer.ID,
                    previous_type="vip",
                    new_type="customer",
                    reason="2 warnings from dismissed complaints",
                    changed_by=current_user.ID,
                    created_at=get_iso_now()
                )
                db.add(vip_record)
            
            elif filer.type == "customer" and filer.warnings >= 3:
                filer.is_blacklisted = True
                blacklisted = True
                
                blacklist_entry = Blacklist(
                    email=filer.email,
                    reason="3 warnings from dismissed complaints",
                    original_account_id=filer.ID,
                    blacklisted_by=current_user.ID,
                    created_at=get_iso_now()
                )
                db.add(blacklist_entry)
    
    # Create audit entry
    audit_entry = create_audit_entry(
        db,
        action_type="dispute_resolved",
        actor_id=current_user.ID,
        target_id=warning_applied_to,
        complaint_id=complaint.id,
        order_id=complaint.order_id,
        details={
            "resolution": request.resolution,
            "notes": request.notes,
            "warning_applied_to": warning_applied_to,
            "new_warning_count": new_warning_count,
            "vip_downgrade": vip_downgrade,
            "blacklisted": blacklisted,
            "employee_demoted": employee_demoted,
            "employee_fired": employee_fired
        }
    )
    
    db.commit()
    
    return DisputeResolveResponse(
        message=f"Dispute resolved as '{request.resolution}'",
        complaint_id=complaint.id,
        resolution=request.resolution,
        warning_applied_to=warning_applied_to,
        new_warning_count=new_warning_count,
        vip_downgrade=vip_downgrade,
        blacklisted=blacklisted,
        employee_demoted=employee_demoted,
        employee_fired=employee_fired,
        audit_log_id=audit_entry.id
    )


@router.post("/complaints/{complaint_id}/dispute")
async def mark_as_disputed(
    complaint_id: int,
    reason: Optional[str] = None,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a complaint as disputed (delivery personnel can dispute complaints about them).
    This endpoint is kept for backwards compatibility.
    Use POST /complaints/{complaint_id}/dispute in the reputation router for the full dispute flow.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    # Only the person being complained about can dispute
    if complaint.accountID != current_user.ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the person being complained about can dispute"
        )
    
    if complaint.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot dispute complaint with status: {complaint.status}"
        )
    
    # Can't dispute compliments
    if complaint.type == "compliment":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot dispute a compliment"
        )
    
    # Set disputed fields
    complaint.status = "disputed"
    complaint.disputed = True
    complaint.dispute_reason = reason
    complaint.disputed_at = get_iso_now()
    
    # Create notification for manager
    create_manager_notification(
        db,
        notification_type="complaint_disputed",
        title="Complaint Disputed",
        message=f"Complaint #{complaint.id} has been disputed by {current_user.email}. Reason: {reason or 'No reason provided'}",
        related_account_id=current_user.ID,
        related_order_id=complaint.order_id
    )
    
    create_audit_entry(
        db,
        action_type="complaint_disputed",
        actor_id=current_user.ID,
        target_id=complaint.filer,
        complaint_id=complaint.id,
        details={"reason": reason}
    )
    
    db.commit()
    
    return {
        "message": "Complaint marked as disputed",
        "complaint_id": complaint.id,
        "status": "disputed",
        "disputed": True,
        "dispute_reason": reason,
        "disputed_at": complaint.disputed_at
    }


# ============================================================
# Bidding Management Endpoints
# ============================================================

@router.get("/bidding/orders", response_model=BiddingOrderListResponse)
async def get_bidding_orders(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Get orders that have bids but haven't been assigned yet.
    """
    # Orders with paid status that have at least one bid but no assigned bid
    orders = db.query(Order).filter(
        Order.status == "paid",
        Order.bidID == None
    ).join(Bid, Bid.orderID == Order.id).distinct().order_by(Order.dateTime.desc()).offset(offset).limit(limit).all()
    
    total = db.query(Order).filter(
        Order.status == "paid",
        Order.bidID == None
    ).join(Bid, Bid.orderID == Order.id).distinct().count()
    
    results = []
    for order in orders:
        customer = db.query(Account).filter(Account.ID == order.accountID).first()
        
        # Get bids for this order
        bids = db.query(Bid).filter(Bid.orderID == order.id).order_by(Bid.bidAmount.asc()).all()
        lowest_bid = bids[0] if bids else None
        
        results.append(BiddingOrderResponse(
            order_id=order.id,
            customer_email=customer.email if customer else "Unknown",
            order_total=order.finalCost,
            delivery_address=order.delivery_address or "",
            created_at=order.dateTime or "",
            bids_count=len(bids),
            lowest_bid_amount=lowest_bid.bidAmount if lowest_bid else None,
            lowest_bid_delivery_id=lowest_bid.deliveryPersonID if lowest_bid else None
        ))
    
    return BiddingOrderListResponse(
        orders=results,
        total=total
    )


@router.post("/bidding/orders/{order_id}/assign", response_model=BidAssignResponse)
async def assign_bid(
    order_id: int,
    request: BidAssignRequest,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Assign a bid to an order. Manager chooses which delivery person wins.
    If choosing a non-lowest bid, memo is required.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status != "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order is not open for assignment. Status: {order.status}"
        )
    
    # Get the selected bid
    selected_bid = db.query(Bid).filter(Bid.id == request.bid_id).first()
    
    if not selected_bid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid not found"
        )
    
    if selected_bid.orderID != order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bid does not belong to this order"
        )
    
    # Find the lowest bid
    lowest_bid = db.query(Bid).filter(
        Bid.orderID == order_id
    ).order_by(Bid.bidAmount.asc()).first()
    
    is_lowest = selected_bid.id == lowest_bid.id
    memo_required = not is_lowest
    memo_saved = False
    
    # Validate memo if not lowest bid
    if memo_required and not request.memo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Memo is required when choosing a non-lowest bid"
        )
    
    # Assign the bid
    order.bidID = selected_bid.id
    order.status = "assigned"
    order.delivery_fee = selected_bid.bidAmount
    
    if request.memo:
        order.assignment_memo = request.memo
        memo_saved = True
    
    # Create audit entry
    create_audit_entry(
        db,
        action_type="bid_assigned",
        actor_id=current_user.ID,
        order_id=order.id,
        details={
            "bid_id": selected_bid.id,
            "delivery_person_id": selected_bid.deliveryPersonID,
            "bid_amount": selected_bid.bidAmount,
            "is_lowest_bid": is_lowest,
            "memo": request.memo
        }
    )
    
    db.commit()
    
    return BidAssignResponse(
        message="Bid assigned successfully",
        order_id=order.id,
        bid_id=selected_bid.id,
        delivery_person_id=selected_bid.deliveryPersonID,
        delivery_fee=selected_bid.bidAmount,
        is_lowest_bid=is_lowest,
        memo_required=memo_required,
        memo_saved=memo_saved
    )


# ============================================================
# KB Moderation Endpoints
# ============================================================

@router.get("/kb/moderation", response_model=KBModerationListResponse)
async def get_kb_for_moderation(
    include_inactive: bool = Query(False),
    flagged_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Get KB entries for moderation with flagged counts and ratings.
    """
    query = db.query(KnowledgeBase)
    
    if not include_inactive:
        query = query.filter(KnowledgeBase.is_active == True)
    
    # If flagged_only, find KB entries that have flagged chat logs
    if flagged_only:
        flagged_kb_ids = db.query(ChatLog.kb_entry_id).filter(
            ChatLog.flagged == True,
            ChatLog.kb_entry_id != None
        ).distinct().subquery()
        query = query.filter(KnowledgeBase.id.in_(flagged_kb_ids))
    
    total = query.count()
    entries = query.order_by(KnowledgeBase.id.desc()).offset(offset).limit(limit).all()
    
    # Count total flagged
    flagged_count = db.query(KnowledgeBase).filter(
        KnowledgeBase.id.in_(
            db.query(ChatLog.kb_entry_id).filter(
                ChatLog.flagged == True,
                ChatLog.kb_entry_id != None
            ).distinct()
        )
    ).count()
    
    results = []
    for entry in entries:
        author = db.query(Account).filter(Account.ID == entry.author_id).first() if entry.author_id else None
        
        # Count flags for this entry
        entry_flagged = db.query(ChatLog).filter(
            ChatLog.kb_entry_id == entry.id,
            ChatLog.flagged == True
        ).count()
        
        # Get average rating for chats using this KB entry
        avg_rating_result = db.query(func.avg(ChatLog.rating)).filter(
            ChatLog.kb_entry_id == entry.id,
            ChatLog.rating > 0
        ).scalar()
        
        results.append(KBModerationResponse(
            id=entry.id,
            question=entry.question,
            answer=entry.answer,
            keywords=entry.keywords,
            confidence=float(entry.confidence),
            author_id=entry.author_id,
            author_email=author.email if author else None,
            is_active=entry.is_active,
            flagged_count=entry_flagged,
            avg_rating=float(avg_rating_result) if avg_rating_result else None,
            created_at=entry.created_at.isoformat() if hasattr(entry.created_at, 'isoformat') else entry.created_at
        ))
    
    return KBModerationListResponse(
        entries=results,
        total=total,
        flagged_count=flagged_count
    )


@router.delete("/kb/{kb_id}")
async def remove_kb_entry(
    kb_id: int,
    permanent: bool = Query(False, description="Permanently delete instead of soft-delete"),
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Remove a KB entry (soft-delete by default).
    """
    entry = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KB entry not found"
        )
    
    if permanent:
        db.delete(entry)
        action = "deleted"
    else:
        entry.is_active = False
        entry.updated_at = get_iso_now()
        action = "deactivated"
    
    create_audit_entry(
        db,
        action_type=f"kb_entry_{action}",
        actor_id=current_user.ID,
        details={
            "kb_id": kb_id,
            "question": entry.question[:100],
            "permanent": permanent
        }
    )
    
    db.commit()
    
    return {"message": f"KB entry {kb_id} {action}", "kb_id": kb_id}


@router.post("/kb/{kb_id}/restore")
async def restore_kb_entry(
    kb_id: int,
    current_user: Account = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Restore a soft-deleted KB entry.
    """
    entry = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KB entry not found"
        )
    
    if entry.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KB entry is already active"
        )
    
    entry.is_active = True
    entry.updated_at = get_iso_now()
    
    create_audit_entry(
        db,
        action_type="kb_entry_restored",
        actor_id=current_user.ID,
        details={"kb_id": kb_id}
    )
    
    db.commit()
    
    return {"message": f"KB entry {kb_id} restored", "kb_id": kb_id}
