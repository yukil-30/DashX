"""
Home Router - Personalized recommendations
Includes:
- GET /home - Personalized dish recommendations

For logged-in customers with order history:
  - Top 3 dishes most ordered by that customer
  - Top 3 dishes highest rated by that customer

For new users or visitors:
  - Global most popular dishes (by order count)
  - Global top rated dishes
"""

import logging
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Dish, DishReview, OrderedDish, Order, Account
from app.schemas import HomeResponse, DishResponse, DishImageResponse
from app.auth import get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/home", tags=["Home"])


def format_price(price_cents: int) -> str:
    """Format price in cents to dollar string"""
    return f"${price_cents / 100:.2f}"


def dish_to_response(dish: Dish) -> DishResponse:
    """Convert Dish model to DishResponse schema"""
    chef_name = None
    if dish.chef:
        chef_name = f"{dish.chef.first_name or ''} {dish.chef.last_name or ''}".strip() or dish.chef.email
    
    return DishResponse(
        id=dish.id,
        name=dish.name,
        description=dish.description,
        price_cents=dish.price,
        price_formatted=format_price(dish.price),
        category=dish.category,
        is_available=dish.is_available,
        is_special=dish.is_special,
        average_rating=float(dish.average_rating or 0),
        review_count=dish.review_count,
        order_count=dish.order_count,
        chef_id=dish.chef_id,
        chef_name=chef_name,
        images=[DishImageResponse.model_validate(img) for img in (dish.images or [])],
        picture=dish.picture,
        created_at=dish.created_at,
        updated_at=dish.updated_at
    )


def get_global_popular_dishes(db: Session, limit: int = 3) -> List[Dish]:
    """
    Get globally most popular dishes by order count.
    Uses denormalized order_count field for efficiency.
    
    SQL equivalent:
    SELECT * FROM dishes 
    WHERE is_available = TRUE 
    ORDER BY order_count DESC, average_rating DESC 
    LIMIT 3;
    """
    return db.query(Dish).options(
        joinedload(Dish.chef),
        joinedload(Dish.images)
    ).filter(
        Dish.is_available == True
    ).order_by(
        desc(Dish.order_count),
        desc(Dish.average_rating)
    ).limit(limit).all()


def get_global_top_rated_dishes(db: Session, limit: int = 3) -> List[Dish]:
    """
    Get globally top-rated dishes.
    Requires minimum review count for quality assurance.
    
    SQL equivalent:
    SELECT * FROM dishes 
    WHERE is_available = TRUE AND review_count >= 1
    ORDER BY average_rating DESC, review_count DESC 
    LIMIT 3;
    """
    return db.query(Dish).options(
        joinedload(Dish.chef),
        joinedload(Dish.images)
    ).filter(
        Dish.is_available == True,
        Dish.review_count >= 1  # Minimum reviews for quality
    ).order_by(
        desc(Dish.average_rating),
        desc(Dish.review_count)
    ).limit(limit).all()


def get_customer_most_ordered_dishes(db: Session, account_id: int, limit: int = 3) -> List[Dish]:
    """
    Get dishes most ordered by a specific customer.
    
    SQL equivalent:
    SELECT d.*, SUM(od.quantity) as total_ordered
    FROM dishes d
    JOIN ordered_dishes od ON d.id = od.dish_id
    JOIN orders o ON od.order_id = o.id
    WHERE o.account_id = :account_id AND d.is_available = TRUE
    GROUP BY d.id
    ORDER BY total_ordered DESC
    LIMIT 3;
    """
    # Subquery for order counts per dish
    subquery = db.query(
        OrderedDish.dish_id,
        func.sum(OrderedDish.quantity).label('total_ordered')
    ).join(
        Order, OrderedDish.order_id == Order.id
    ).filter(
        Order.account_id == account_id
    ).group_by(
        OrderedDish.dish_id
    ).subquery()
    
    # Get dishes with their order counts
    dishes = db.query(Dish).options(
        joinedload(Dish.chef),
        joinedload(Dish.images)
    ).join(
        subquery, Dish.id == subquery.c.dish_id
    ).filter(
        Dish.is_available == True
    ).order_by(
        desc(subquery.c.total_ordered)
    ).limit(limit).all()
    
    return dishes


def get_customer_highest_rated_dishes(db: Session, account_id: int, limit: int = 3) -> List[Dish]:
    """
    Get dishes highest rated by a specific customer.
    
    SQL equivalent:
    SELECT d.*, dr.rating
    FROM dishes d
    JOIN dish_reviews dr ON d.id = dr.dish_id
    WHERE dr.account_id = :account_id AND d.is_available = TRUE
    ORDER BY dr.rating DESC, dr.created_at DESC
    LIMIT 3;
    """
    dishes = db.query(Dish).options(
        joinedload(Dish.chef),
        joinedload(Dish.images)
    ).join(
        DishReview, Dish.id == DishReview.dish_id
    ).filter(
        DishReview.account_id == account_id,
        Dish.is_available == True
    ).order_by(
        desc(DishReview.rating),
        desc(DishReview.created_at)
    ).limit(limit).all()
    
    return dishes


def customer_has_order_history(db: Session, account_id: int) -> bool:
    """Check if customer has any completed orders"""
    return db.query(Order).filter(
        Order.account_id == account_id
    ).first() is not None


@router.get("", response_model=HomeResponse)
async def get_home(
    current_user: Account = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get personalized home page content.
    
    For logged-in customers with order history:
      - Returns top 3 dishes most ordered by that customer
      - Returns top 3 dishes highest rated by that customer
      
    For new users or visitors:
      - Returns global most popular dishes
      - Returns global top rated dishes
    
    Performance notes:
    - Uses denormalized order_count on dishes for efficient popularity queries
    - Indexed queries for fast lookups
    - Eager loads relationships to minimize N+1 queries
    """
    is_personalized = False
    most_ordered = []
    top_rated = []
    
    # Check if user is logged in and has order history
    if current_user and customer_has_order_history(db, current_user.id):
        # Personalized recommendations
        is_personalized = True
        
        # Get customer's most ordered dishes
        customer_ordered = get_customer_most_ordered_dishes(db, current_user.id, limit=3)
        most_ordered = [dish_to_response(d) for d in customer_ordered]
        
        # Get customer's highest rated dishes
        customer_rated = get_customer_highest_rated_dishes(db, current_user.id, limit=3)
        top_rated = [dish_to_response(d) for d in customer_rated]
        
        # If not enough personalized results, supplement with global
        if len(most_ordered) < 3:
            existing_ids = {d.id for d in customer_ordered}
            global_popular = get_global_popular_dishes(db, limit=3 - len(most_ordered) + 5)
            for dish in global_popular:
                if dish.id not in existing_ids and len(most_ordered) < 3:
                    most_ordered.append(dish_to_response(dish))
                    existing_ids.add(dish.id)
        
        if len(top_rated) < 3:
            existing_ids = {d.id for d in customer_rated}
            global_rated = get_global_top_rated_dishes(db, limit=3 - len(top_rated) + 5)
            for dish in global_rated:
                if dish.id not in existing_ids and len(top_rated) < 3:
                    top_rated.append(dish_to_response(dish))
                    existing_ids.add(dish.id)
        
        logger.debug(f"Personalized home for user {current_user.id}: {len(most_ordered)} ordered, {len(top_rated)} rated")
    else:
        # Global recommendations for visitors/new users
        is_personalized = False
        
        global_popular = get_global_popular_dishes(db, limit=3)
        most_ordered = [dish_to_response(d) for d in global_popular]
        
        global_rated = get_global_top_rated_dishes(db, limit=3)
        top_rated = [dish_to_response(d) for d in global_rated]
        
        logger.debug(f"Global home: {len(most_ordered)} popular, {len(top_rated)} rated")
    
    return HomeResponse(
        most_ordered=most_ordered,
        top_rated=top_rated,
        is_personalized=is_personalized
    )
