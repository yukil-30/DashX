"""
Background Tasks for DashX
Handles periodic evaluation of chef/delivery performance
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import SessionLocal
from app.models import Account, Complaint, Dish, ManagerNotification, DeliveryRating

logger = logging.getLogger(__name__)


def get_iso_now() -> str:
    """Get current timestamp as ISO string"""
    return datetime.now(timezone.utc).isoformat()


def create_notification(
    db: Session,
    notification_type: str,
    title: str,
    message: str,
    related_account_id: Optional[int] = None
) -> ManagerNotification:
    """Create a manager notification"""
    notification = ManagerNotification(
        notification_type=notification_type,
        title=title,
        message=message,
        related_account_id=related_account_id,
        is_read=False,
        created_at=get_iso_now()
    )
    db.add(notification)
    return notification


def evaluate_chef_performance(db: Session) -> list:
    """
    Evaluate all chef performance and create notifications for those at risk.
    
    Thresholds:
    - 3+ complaints -> Needs attention
    - Average rating < 2.0 -> Needs attention
    - 2+ complaints OR rating < 2.5 -> Warning
    
    Returns list of evaluation results.
    """
    results = []
    
    chefs = db.query(Account).filter(
        Account.type == "chef",
        Account.is_fired == False
    ).all()
    
    for chef in chefs:
        # Count resolved complaints with warning
        complaint_count = db.query(Complaint).filter(
            Complaint.accountID == chef.ID,
            Complaint.type == "complaint",
            Complaint.status == "resolved",
            Complaint.resolution == "warning_issued"
        ).count()
        
        # Calculate average dish rating
        avg_rating_result = db.query(func.avg(Dish.average_rating)).filter(
            Dish.chefID == chef.ID,
            Dish.reviews > 0
        ).scalar()
        
        avg_rating = float(avg_rating_result) if avg_rating_result else None
        
        # Determine status
        status = "ok"
        if complaint_count >= 3 or (avg_rating and avg_rating < 2.0):
            status = "critical"
            create_notification(
                db,
                notification_type="chef_performance_critical",
                title=f"Chef Performance Critical: {chef.email}",
                message=f"Chef has {complaint_count} complaints and average rating of {avg_rating:.1f if avg_rating else 'N/A'}. Immediate attention required.",
                related_account_id=chef.ID
            )
        elif complaint_count >= 2 or (avg_rating and avg_rating < 2.5):
            status = "warning"
            create_notification(
                db,
                notification_type="chef_performance_warning",
                title=f"Chef Performance Warning: {chef.email}",
                message=f"Chef has {complaint_count} complaints and average rating of {avg_rating:.1f if avg_rating else 'N/A'}. Consider review.",
                related_account_id=chef.ID
            )
        
        results.append({
            "chef_id": chef.ID,
            "email": chef.email,
            "complaint_count": complaint_count,
            "avg_rating": avg_rating,
            "times_demoted": chef.times_demoted,
            "status": status
        })
    
    return results


def evaluate_delivery_performance(db: Session) -> list:
    """
    Evaluate all delivery person performance and create notifications.
    
    Thresholds:
    - On-time percentage < 70% -> Needs attention
    - Average rating < 3.0 -> Warning
    
    Returns list of evaluation results.
    """
    results = []
    
    delivery_people = db.query(Account).filter(
        Account.type == "delivery",
        Account.is_fired == False
    ).all()
    
    for person in delivery_people:
        # Get delivery stats
        rating = db.query(DeliveryRating).filter(
            DeliveryRating.accountID == person.ID
        ).first()
        
        if not rating or rating.total_deliveries == 0:
            results.append({
                "delivery_id": person.ID,
                "email": person.email,
                "total_deliveries": 0,
                "on_time_pct": None,
                "avg_rating": None,
                "status": "ok"
            })
            continue
        
        on_time_pct = (rating.on_time_deliveries / rating.total_deliveries * 100) if rating.total_deliveries > 0 else 0
        avg_rating = float(rating.averageRating) if rating.averageRating else None
        
        # Determine status
        status = "ok"
        if on_time_pct < 70 or (avg_rating and avg_rating < 3.0):
            status = "warning"
            create_notification(
                db,
                notification_type="delivery_performance_warning",
                title=f"Delivery Performance Warning: {person.email}",
                message=f"On-time: {on_time_pct:.0f}%, Rating: {avg_rating:.1f if avg_rating else 'N/A'}. Consider review.",
                related_account_id=person.ID
            )
        
        results.append({
            "delivery_id": person.ID,
            "email": person.email,
            "total_deliveries": rating.total_deliveries,
            "on_time_pct": on_time_pct,
            "avg_rating": avg_rating,
            "status": status
        })
    
    return results


async def periodic_performance_evaluation():
    """
    Background task that runs periodically to evaluate performance.
    Runs every hour (configurable).
    """
    interval_seconds = 3600  # 1 hour
    
    while True:
        try:
            logger.info("Starting periodic performance evaluation...")
            
            db = SessionLocal()
            try:
                chef_results = evaluate_chef_performance(db)
                delivery_results = evaluate_delivery_performance(db)
                
                db.commit()
                
                critical_chefs = [r for r in chef_results if r["status"] == "critical"]
                warning_chefs = [r for r in chef_results if r["status"] == "warning"]
                warning_delivery = [r for r in delivery_results if r["status"] == "warning"]
                
                logger.info(
                    f"Performance evaluation complete: "
                    f"{len(chef_results)} chefs ({len(critical_chefs)} critical, {len(warning_chefs)} warnings), "
                    f"{len(delivery_results)} delivery ({len(warning_delivery)} warnings)"
                )
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in periodic performance evaluation: {e}", exc_info=True)
        
        await asyncio.sleep(interval_seconds)


def run_immediate_evaluation():
    """
    Run performance evaluation immediately (for testing or manual trigger).
    """
    db = SessionLocal()
    try:
        chef_results = evaluate_chef_performance(db)
        delivery_results = evaluate_delivery_performance(db)
        db.commit()
        
        return {
            "chef_evaluations": chef_results,
            "delivery_evaluations": delivery_results,
            "timestamp": get_iso_now()
        }
    finally:
        db.close()
