"""
Reputation Engine
Centralized reputation management with automated rule enforcement.

Business Rules:

EMPLOYEES (Chefs & Delivery):
- Rolling average rating calculated dynamically on each new rating
- Compliments decrement complaint_count by 1 (floor at 0)
- If avg_rating < 2 OR complaint_count >= 3 → automatic demotion
- If avg_rating > 4 OR compliment_count >= 3 (since last reset) → automatic bonus
- A compliment immediately cancels one complaint
- Two demotions → auto-fired (account disabled, removed from bidding pools)

CUSTOMERS:
- Warning count (0-3)
- Customer tier: registered / vip / deregistered
- Complaint WITH merit → +1 warning
- Complaint WITHOUT merit (dismissed) → +1 warning to complainant
- 3 warnings → automatic deregistration, account disabled, balance removed
- VIP with 2 warnings → demote to registered, reset warnings to 0

TRIGGER POINTS:
- Every rating submission
- Every new complaint
- Every compliment
- Every complaint/compliment resolution
- Every warning update
- Every dispute resolution
- Every demotion/bonus update
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Account, Complaint, AuditLog, Blacklist, ManagerNotification,
    Dish, Order, Bid, DeliveryRating
)

logger = logging.getLogger(__name__)


# ============================================================
# Constants
# ============================================================

# Employee thresholds
EMPLOYEE_LOW_RATING_THRESHOLD = 2.0  # Below this → demotion
EMPLOYEE_HIGH_RATING_THRESHOLD = 4.0  # Above this → bonus eligible
EMPLOYEE_COMPLAINT_THRESHOLD = 3  # At or above → demotion
EMPLOYEE_COMPLIMENT_BONUS_THRESHOLD = 3  # At or above → bonus
EMPLOYEE_DEMOTION_FIRE_THRESHOLD = 2  # At or above → fired
EMPLOYEE_WAGE_DEMOTION_PERCENT = 0.10  # 10% wage reduction on demotion
EMPLOYEE_BONUS_PERCENT = 0.10  # 10% wage increase on bonus

# Customer thresholds
CUSTOMER_WARNING_THRESHOLD = 3  # At or above → deregistration
VIP_WARNING_DOWNGRADE_THRESHOLD = 2  # At or above → VIP demoted to registered


# ============================================================
# Utility Functions
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
        details=details or {},
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
# Rating Calculation
# ============================================================

def update_employee_rating(
    db: Session,
    employee: Account,
    new_rating: int,
    actor_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Update employee's rolling average rating with a new rating.
    Triggers rule engine evaluation afterward.
    
    Returns dict with rating update details and any triggered actions.
    """
    if employee.type not in ["chef", "delivery"]:
        return {"error": "Not an employee account"}
    
    old_avg = float(employee.rolling_avg_rating or 0)
    old_count = employee.total_rating_count or 0
    
    # Calculate new rolling average
    new_count = old_count + 1
    if old_count == 0:
        new_avg = float(new_rating)
    else:
        new_avg = ((old_avg * old_count) + new_rating) / new_count
    
    # Update employee
    employee.rolling_avg_rating = Decimal(str(round(new_avg, 2)))
    employee.total_rating_count = new_count
    
    # Audit the rating update
    create_audit_entry(
        db,
        action_type="employee_rating_updated",
        actor_id=actor_id,
        target_id=employee.ID,
        details={
            "new_rating": new_rating,
            "old_avg": old_avg,
            "new_avg": new_avg,
            "total_ratings": new_count
        }
    )
    
    # Run rule engine
    rule_results = evaluate_employee_rules(db, employee, actor_id)
    
    return {
        "old_avg": old_avg,
        "new_avg": new_avg,
        "total_ratings": new_count,
        "rule_results": rule_results
    }


def recalculate_chef_rating_from_dishes(db: Session, chef: Account) -> Tuple[float, int]:
    """
    Recalculate a chef's rating from their dish ratings.
    Returns (average_rating, total_reviews).
    """
    result = db.query(
        func.avg(Dish.average_rating),
        func.sum(Dish.reviews)
    ).filter(
        Dish.chefID == chef.ID,
        Dish.reviews > 0
    ).first()
    
    avg_rating = float(result[0]) if result[0] else 0.0
    total_reviews = int(result[1] or 0)
    
    # Update chef's rolling average
    chef.rolling_avg_rating = Decimal(str(round(avg_rating, 2)))
    chef.total_rating_count = total_reviews
    
    return avg_rating, total_reviews


def recalculate_delivery_rating(db: Session, delivery_person: Account) -> Tuple[float, int]:
    """
    Get delivery person's rating from DeliveryRating table.
    Returns (average_rating, total_reviews).
    """
    delivery_rating = db.query(DeliveryRating).filter(
        DeliveryRating.accountID == delivery_person.ID
    ).first()
    
    if delivery_rating:
        avg_rating = float(delivery_rating.averageRating or 0)
        total_reviews = delivery_rating.reviews or 0
        
        # Sync to account
        delivery_person.rolling_avg_rating = delivery_rating.averageRating
        delivery_person.total_rating_count = total_reviews
        
        return avg_rating, total_reviews
    
    return 0.0, 0


# ============================================================
# Complaint/Compliment Handling
# ============================================================

def process_compliment(
    db: Session,
    employee: Account,
    actor_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Process a compliment for an employee.
    - Increment compliment count
    - Decrement complaint count by 1 (floor at 0)
    - Check for bonus eligibility
    
    Returns dict with action details.
    """
    if employee.type not in ["chef", "delivery"]:
        return {"error": "Not an employee account"}
    
    old_complaint_count = employee.complaint_count
    old_compliment_count = employee.compliment_count
    
    # Increment compliment count
    employee.compliment_count = (employee.compliment_count or 0) + 1
    
    # Decrement complaint count (floor at 0)
    if employee.complaint_count and employee.complaint_count > 0:
        employee.complaint_count -= 1
        complaint_canceled = True
    else:
        complaint_canceled = False
    
    # Audit
    create_audit_entry(
        db,
        action_type="employee_compliment_processed",
        actor_id=actor_id,
        target_id=employee.ID,
        details={
            "old_complaint_count": old_complaint_count,
            "new_complaint_count": employee.complaint_count,
            "old_compliment_count": old_compliment_count,
            "new_compliment_count": employee.compliment_count,
            "complaint_canceled": complaint_canceled
        }
    )
    
    # Run rule engine
    rule_results = evaluate_employee_rules(db, employee, actor_id)
    
    return {
        "complaint_canceled": complaint_canceled,
        "new_complaint_count": employee.complaint_count,
        "new_compliment_count": employee.compliment_count,
        "rule_results": rule_results
    }


def process_complaint_against_employee(
    db: Session,
    employee: Account,
    actor_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Process a valid (upheld) complaint against an employee.
    - Increment complaint count
    - Check for demotion
    
    Returns dict with action details.
    """
    if employee.type not in ["chef", "delivery"]:
        return {"error": "Not an employee account"}
    
    old_complaint_count = employee.complaint_count
    
    # Increment complaint count
    employee.complaint_count = (employee.complaint_count or 0) + 1
    
    # Audit
    create_audit_entry(
        db,
        action_type="employee_complaint_processed",
        actor_id=actor_id,
        target_id=employee.ID,
        details={
            "old_complaint_count": old_complaint_count,
            "new_complaint_count": employee.complaint_count
        }
    )
    
    # Run rule engine
    rule_results = evaluate_employee_rules(db, employee, actor_id)
    
    return {
        "new_complaint_count": employee.complaint_count,
        "rule_results": rule_results
    }


# ============================================================
# Employee Rule Engine
# ============================================================

def evaluate_employee_rules(
    db: Session,
    employee: Account,
    actor_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Evaluate all employee rules and apply actions.
    
    Rules:
    - avg_rating < 2 OR complaint_count >= 3 → demotion
    - avg_rating > 4 OR compliment_count >= 3 → bonus
    - 2 demotions → fired
    
    Returns dict with all actions taken.
    """
    if employee.type not in ["chef", "delivery"] or employee.is_fired:
        return {"skipped": True, "reason": "Not active employee"}
    
    results = {
        "demoted": False,
        "fired": False,
        "bonus_awarded": False,
        "actions": []
    }
    
    avg_rating = float(employee.rolling_avg_rating or 0)
    complaint_count = employee.complaint_count or 0
    compliment_count = employee.compliment_count or 0
    
    # Check demotion conditions
    should_demote = (
        (avg_rating > 0 and avg_rating < EMPLOYEE_LOW_RATING_THRESHOLD) or
        complaint_count >= EMPLOYEE_COMPLAINT_THRESHOLD
    )
    
    if should_demote:
        demotion_result = apply_employee_demotion(db, employee, actor_id, {
            "avg_rating": avg_rating,
            "complaint_count": complaint_count
        })
        results["demoted"] = demotion_result.get("demoted", False)
        results["fired"] = demotion_result.get("fired", False)
        results["actions"].append(demotion_result)
    
    # Check bonus conditions (only if not demoted/fired)
    if not results["demoted"] and not results["fired"]:
        should_bonus = (
            (avg_rating > EMPLOYEE_HIGH_RATING_THRESHOLD) or
            compliment_count >= EMPLOYEE_COMPLIMENT_BONUS_THRESHOLD
        )
        
        if should_bonus:
            bonus_result = apply_employee_bonus(db, employee, actor_id, {
                "avg_rating": avg_rating,
                "compliment_count": compliment_count
            })
            results["bonus_awarded"] = bonus_result.get("bonus_awarded", False)
            results["actions"].append(bonus_result)
    
    return results


def apply_employee_demotion(
    db: Session,
    employee: Account,
    actor_id: Optional[int] = None,
    reason_details: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Apply demotion to employee.
    - Reduce wage by 10%
    - Increment demotion count
    - If 2 demotions → fire
    """
    old_wage = employee.wage
    
    # Increment demotion counts
    employee.times_demoted = (employee.times_demoted or 0) + 1
    employee.demotion_count = employee.times_demoted  # Keep in sync
    
    # Check if should be fired
    if employee.times_demoted >= EMPLOYEE_DEMOTION_FIRE_THRESHOLD:
        return apply_employee_firing(db, employee, actor_id, {
            **(reason_details or {}),
            "reason": f"Reached {EMPLOYEE_DEMOTION_FIRE_THRESHOLD} demotions"
        })
    
    # Apply wage reduction
    if employee.wage and employee.wage > 0:
        reduction = int(employee.wage * EMPLOYEE_WAGE_DEMOTION_PERCENT)
        employee.wage = max(employee.wage - reduction, 0)
    
    employee.employment_status = "demoted"
    
    # Create audit entry
    create_audit_entry(
        db,
        action_type="employee_demoted",
        actor_id=actor_id,
        target_id=employee.ID,
        details={
            "old_wage": old_wage,
            "new_wage": employee.wage,
            "times_demoted": employee.times_demoted,
            **(reason_details or {})
        }
    )
    
    # Notify manager
    create_manager_notification(
        db,
        notification_type="employee_demoted",
        title=f"Employee Demoted",
        message=f"{employee.type.capitalize()} {employee.email} has been demoted (time #{employee.times_demoted}). Wage reduced from ${old_wage/100:.2f} to ${employee.wage/100:.2f}." if old_wage else f"{employee.type.capitalize()} {employee.email} has been demoted.",
        related_account_id=employee.ID
    )
    
    logger.warning(f"Employee {employee.email} demoted. Times demoted: {employee.times_demoted}")
    
    return {
        "demoted": True,
        "fired": False,
        "old_wage": old_wage,
        "new_wage": employee.wage,
        "times_demoted": employee.times_demoted
    }


def apply_employee_firing(
    db: Session,
    employee: Account,
    actor_id: Optional[int] = None,
    reason_details: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Fire an employee.
    - Mark as fired
    - Set employment_status to 'fired'
    - Remove from all active bidding pools
    - Block future order assignments
    """
    old_type = employee.type
    
    employee.is_fired = True
    employee.previous_type = employee.type
    employee.type = "fired"
    employee.employment_status = "fired"
    
    # Remove from active bidding pools - delete all pending bids
    if old_type == "delivery":
        # Get all orders that have this person's pending bids but not yet assigned
        pending_bids = db.query(Bid).filter(
            Bid.deliveryPersonID == employee.ID
        ).all()
        
        # Delete bids for unassigned orders
        for bid in pending_bids:
            order = db.query(Order).filter(Order.id == bid.orderID).first()
            if order and order.bidID != bid.id:  # Not the winning bid
                db.delete(bid)
    
    # Create audit entry
    create_audit_entry(
        db,
        action_type="employee_fired",
        actor_id=actor_id,
        target_id=employee.ID,
        details={
            "previous_type": old_type,
            "times_demoted": employee.times_demoted,
            **(reason_details or {})
        }
    )
    
    # Notify manager
    create_manager_notification(
        db,
        notification_type="employee_fired",
        title=f"Employee Fired",
        message=f"{old_type.capitalize()} {employee.email} has been fired after {employee.times_demoted} demotions. Account disabled.",
        related_account_id=employee.ID
    )
    
    logger.warning(f"Employee {employee.email} FIRED")
    
    return {
        "demoted": False,
        "fired": True,
        "previous_type": old_type,
        "times_demoted": employee.times_demoted
    }


def apply_employee_bonus(
    db: Session,
    employee: Account,
    actor_id: Optional[int] = None,
    reason_details: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Apply bonus to employee.
    - Increase wage by 10%
    - Reset compliment count to avoid repeated bonuses
    """
    old_wage = employee.wage
    
    # Apply wage increase
    if employee.wage and employee.wage > 0:
        bonus = int(employee.wage * EMPLOYEE_BONUS_PERCENT)
        employee.wage = employee.wage + bonus
    else:
        bonus = 0
    
    # Track bonus
    employee.bonus_count = (employee.bonus_count or 0) + 1
    employee.last_bonus_at = get_iso_now()
    
    # Reset compliment count to prevent repeated bonuses
    employee.compliment_count = 0
    
    # Ensure status is active
    if employee.employment_status == "demoted":
        employee.employment_status = "active"
    
    # Create audit entry
    create_audit_entry(
        db,
        action_type="employee_bonus",
        actor_id=actor_id,
        target_id=employee.ID,
        details={
            "old_wage": old_wage,
            "new_wage": employee.wage,
            "bonus_amount": bonus,
            "total_bonuses": employee.bonus_count,
            **(reason_details or {})
        }
    )
    
    # Notify manager
    create_manager_notification(
        db,
        notification_type="employee_bonus",
        title=f"Employee Bonus Awarded",
        message=f"{employee.type.capitalize()} {employee.email} received a bonus! Wage increased from ${old_wage/100:.2f} to ${employee.wage/100:.2f}." if old_wage else f"{employee.type.capitalize()} {employee.email} received a bonus!",
        related_account_id=employee.ID
    )
    
    logger.info(f"Employee {employee.email} received bonus. Total bonuses: {employee.bonus_count}")
    
    return {
        "bonus_awarded": True,
        "old_wage": old_wage,
        "new_wage": employee.wage,
        "bonus_amount": bonus,
        "total_bonuses": employee.bonus_count
    }


# ============================================================
# Customer Rule Engine
# ============================================================

def process_customer_warning(
    db: Session,
    customer: Account,
    actor_id: Optional[int] = None,
    reason: str = "complaint_upheld"
) -> Dict[str, Any]:
    """
    Add a warning to a customer and evaluate rules.
    
    Returns dict with action details.
    """
    if customer.type not in ["customer", "vip", "visitor"]:
        return {"error": "Not a customer account"}
    
    old_warnings = customer.warnings
    customer.warnings = (customer.warnings or 0) + 1
    
    # Create audit entry
    create_audit_entry(
        db,
        action_type="customer_warning_added",
        actor_id=actor_id,
        target_id=customer.ID,
        details={
            "old_warnings": old_warnings,
            "new_warnings": customer.warnings,
            "reason": reason
        }
    )
    
    # Evaluate rules
    rule_results = evaluate_customer_rules(db, customer, actor_id)
    
    return {
        "old_warnings": old_warnings,
        "new_warnings": customer.warnings,
        "rule_results": rule_results
    }


def evaluate_customer_rules(
    db: Session,
    customer: Account,
    actor_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Evaluate customer rules.
    
    Rules:
    - 3 warnings → deregistration
    - VIP with 2 warnings → demote to registered, reset warnings
    """
    if customer.is_blacklisted:
        return {"skipped": True, "reason": "Already blacklisted"}
    
    results = {
        "deregistered": False,
        "vip_demoted": False,
        "warnings_reset": False,
        "actions": []
    }
    
    warnings = customer.warnings or 0
    
    # Check VIP downgrade first (at exactly 2 warnings)
    if customer.type == "vip" and warnings >= VIP_WARNING_DOWNGRADE_THRESHOLD:
        downgrade_result = apply_vip_downgrade(db, customer, actor_id)
        results["vip_demoted"] = True
        results["warnings_reset"] = True
        results["actions"].append(downgrade_result)
        return results  # Don't continue to deregistration since warnings reset
    
    # Check deregistration (at 3 warnings)
    if customer.type in ["customer", "visitor"] and warnings >= CUSTOMER_WARNING_THRESHOLD:
        dereg_result = apply_customer_deregistration(db, customer, actor_id)
        results["deregistered"] = True
        results["actions"].append(dereg_result)
    
    return results


def apply_vip_downgrade(
    db: Session,
    customer: Account,
    actor_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Downgrade VIP to regular customer and reset warnings.
    """
    old_warnings = customer.warnings
    
    customer.previous_type = "vip"
    customer.type = "customer"
    customer.is_vip = False
    customer.customer_tier = "registered"
    customer.warnings = 0  # Reset warnings after downgrade
    
    # Create audit entry
    create_audit_entry(
        db,
        action_type="vip_downgraded",
        actor_id=actor_id,
        target_id=customer.ID,
        details={
            "warnings_before_reset": old_warnings,
            "reason": f"Reached {VIP_WARNING_DOWNGRADE_THRESHOLD} warnings as VIP"
        }
    )
    
    # Notify manager
    create_manager_notification(
        db,
        notification_type="vip_downgraded",
        title="VIP Downgraded",
        message=f"VIP customer {customer.email} has been downgraded to regular customer after {old_warnings} warnings. Warnings reset to 0.",
        related_account_id=customer.ID
    )
    
    logger.info(f"VIP {customer.email} downgraded to regular customer. Warnings reset.")
    
    return {
        "vip_demoted": True,
        "warnings_before_reset": old_warnings,
        "new_warnings": 0,
        "new_tier": "registered"
    }


def apply_customer_deregistration(
    db: Session,
    customer: Account,
    actor_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Deregister customer.
    - Disable login
    - Remove balance (manager processes)
    - Mark as blacklisted
    """
    old_balance = customer.balance
    
    customer.is_blacklisted = True
    customer.type = "deregistered"
    customer.customer_tier = "deregistered"
    
    # Balance removal handled by manager - flag for processing
    customer.balance = 0  # Set to 0 (manager will process refund if needed)
    
    # Add to blacklist table
    blacklist_entry = Blacklist(
        email=customer.email,
        reason=f"Reached {CUSTOMER_WARNING_THRESHOLD} warnings. Automatically deregistered.",
        original_account_id=customer.ID,
        blacklisted_by=actor_id,
        created_at=get_iso_now()
    )
    db.add(blacklist_entry)
    
    # Create audit entry
    create_audit_entry(
        db,
        action_type="customer_deregistered",
        actor_id=actor_id,
        target_id=customer.ID,
        details={
            "warnings": customer.warnings,
            "balance_removed": old_balance,
            "reason": f"Reached {CUSTOMER_WARNING_THRESHOLD} warnings"
        }
    )
    
    # Notify manager
    create_manager_notification(
        db,
        notification_type="customer_deregistered",
        title="Customer Deregistered",
        message=f"Customer {customer.email} has been deregistered after {customer.warnings} warnings. Balance of ${old_balance/100:.2f} needs processing.",
        related_account_id=customer.ID
    )
    
    logger.warning(f"Customer {customer.email} DEREGISTERED")
    
    return {
        "deregistered": True,
        "balance_removed": old_balance,
        "warnings": customer.warnings
    }


# ============================================================
# Dispute Resolution
# ============================================================

def resolve_dispute(
    db: Session,
    complaint: Complaint,
    resolution: str,  # "upheld" or "dismissed"
    actor_id: int,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Resolve a disputed complaint.
    
    - upheld: Original complaint was valid → warning to target
    - dismissed: Complaint without merit → warning to filer
    
    Triggers rule engine recalculations.
    """
    results = {
        "complaint_id": complaint.id,
        "resolution": resolution,
        "warning_applied_to": None,
        "actions": []
    }
    
    complaint.status = "resolved"
    complaint.resolution = resolution
    complaint.resolved_by = actor_id
    complaint.resolved_at = get_iso_now()
    
    if resolution == "upheld" or resolution == "warning_issued":
        # Valid complaint → warning to target
        if complaint.accountID:
            target = db.query(Account).filter(Account.ID == complaint.accountID).first()
            if target:
                results["warning_applied_to"] = target.ID
                
                if target.type in ["customer", "vip", "visitor"]:
                    warning_result = process_customer_warning(db, target, actor_id, "complaint_upheld")
                    results["actions"].append({"type": "customer_warning", **warning_result})
                elif target.type in ["chef", "delivery"]:
                    complaint_result = process_complaint_against_employee(db, target, actor_id)
                    results["actions"].append({"type": "employee_complaint", **complaint_result})
    
    elif resolution == "dismissed":
        # Complaint without merit → warning to filer (they made a false complaint)
        filer = db.query(Account).filter(Account.ID == complaint.filer).first()
        if filer and filer.type in ["customer", "vip", "visitor"]:
            results["warning_applied_to"] = filer.ID
            warning_result = process_customer_warning(db, filer, actor_id, "complaint_dismissed_false")
            results["actions"].append({"type": "filer_warning", **warning_result})
    
    # Audit
    create_audit_entry(
        db,
        action_type="dispute_resolved",
        actor_id=actor_id,
        complaint_id=complaint.id,
        target_id=results["warning_applied_to"],
        details={
            "resolution": resolution,
            "notes": notes,
            "actions_taken": len(results["actions"])
        }
    )
    
    return results


def process_compliment_resolution(
    db: Session,
    complaint: Complaint,  # Actually a compliment
    actor_id: int
) -> Dict[str, Any]:
    """
    Process a compliment resolution.
    Applies compliment benefits to the target.
    """
    if complaint.type != "compliment":
        return {"error": "Not a compliment"}
    
    results = {
        "complaint_id": complaint.id,
        "actions": []
    }
    
    complaint.status = "resolved"
    complaint.resolution = "compliment_applied"
    complaint.resolved_by = actor_id
    complaint.resolved_at = get_iso_now()
    
    if complaint.accountID:
        target = db.query(Account).filter(Account.ID == complaint.accountID).first()
        if target and target.type in ["chef", "delivery"]:
            compliment_result = process_compliment(db, target, actor_id)
            results["actions"].append({"type": "employee_compliment", **compliment_result})
    
    return results


# ============================================================
# Batch/Trigger Functions
# ============================================================

def run_all_employee_evaluations(
    db: Session,
    actor_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Run rule evaluation for all active employees.
    Used for batch processing or periodic checks.
    """
    employees = db.query(Account).filter(
        Account.type.in_(["chef", "delivery"]),
        Account.is_fired == False
    ).all()
    
    results = []
    for emp in employees:
        # Recalculate ratings
        if emp.type == "chef":
            recalculate_chef_rating_from_dishes(db, emp)
        elif emp.type == "delivery":
            recalculate_delivery_rating(db, emp)
        
        # Evaluate rules
        rule_results = evaluate_employee_rules(db, emp, actor_id)
        results.append({
            "employee_id": emp.ID,
            "email": emp.email,
            "type": emp.type,
            **rule_results
        })
    
    return results


def get_employee_reputation_summary(
    db: Session,
    employee: Account
) -> Dict[str, Any]:
    """
    Get comprehensive reputation summary for an employee.
    """
    return {
        "employee_id": employee.ID,
        "email": employee.email,
        "type": employee.type,
        "employment_status": employee.employment_status or "active",
        "rolling_avg_rating": float(employee.rolling_avg_rating or 0),
        "total_rating_count": employee.total_rating_count or 0,
        "complaint_count": employee.complaint_count or 0,
        "compliment_count": employee.compliment_count or 0,
        "demotion_count": employee.times_demoted or 0,
        "bonus_count": employee.bonus_count or 0,
        "is_fired": employee.is_fired,
        "wage": employee.wage,
        # Risk assessment
        "near_demotion": (
            (float(employee.rolling_avg_rating or 5) < EMPLOYEE_LOW_RATING_THRESHOLD + 0.5) or
            (employee.complaint_count or 0) >= EMPLOYEE_COMPLAINT_THRESHOLD - 1
        ),
        "near_firing": employee.times_demoted == 1,
        "bonus_eligible": (
            float(employee.rolling_avg_rating or 0) > EMPLOYEE_HIGH_RATING_THRESHOLD or
            (employee.compliment_count or 0) >= EMPLOYEE_COMPLIMENT_BONUS_THRESHOLD - 1
        )
    }


def get_customer_warning_summary(
    db: Session,
    customer: Account
) -> Dict[str, Any]:
    """
    Get warning summary for a customer.
    """
    warnings = customer.warnings or 0
    
    return {
        "customer_id": customer.ID,
        "email": customer.email,
        "type": customer.type,
        "customer_tier": customer.customer_tier or ("vip" if customer.type == "vip" else "registered"),
        "warning_count": warnings,
        "is_blacklisted": customer.is_blacklisted,
        # Warning status
        "near_threshold": (
            (customer.type == "vip" and warnings >= 1) or
            (customer.type in ["customer", "visitor"] and warnings >= 2)
        ),
        "warning_message": _get_warning_message(customer),
        # Thresholds
        "threshold": VIP_WARNING_DOWNGRADE_THRESHOLD if customer.type == "vip" else CUSTOMER_WARNING_THRESHOLD
    }


def _get_warning_message(customer: Account) -> Optional[str]:
    """Generate warning message for customer based on their status."""
    warnings = customer.warnings or 0
    
    if customer.is_blacklisted:
        return "Your account has been suspended."
    
    if warnings == 0:
        return None
    
    if customer.type == "vip":
        if warnings >= 1:
            return f"You have {warnings} warning(s). One more warning will result in VIP status removal."
        return f"You have {warnings} warning(s)."
    
    if customer.type in ["customer", "visitor"]:
        if warnings >= 2:
            return f"You have {warnings} warning(s). One more warning will result in account suspension."
        return f"You have {warnings} warning(s)."
    
    return None


# ============================================================
# Delivery Bidding Pool Exclusion
# ============================================================

def get_eligible_delivery_persons(db: Session) -> List[Account]:
    """
    Get all delivery persons eligible for bidding.
    Excludes fired employees.
    """
    return db.query(Account).filter(
        Account.type == "delivery",
        Account.is_fired == False
    ).all()


def is_delivery_eligible_for_bidding(employee: Account) -> bool:
    """Check if a delivery person is eligible to bid."""
    return (
        employee.type == "delivery" and
        not employee.is_fired and
        employee.employment_status != "fired"
    )
