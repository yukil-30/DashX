"""
Home Router - Personalized recommendations
Includes:
- GET /home - Personalized dish recommendations

For logged-in customers with order history:
  - Top 3 dishes most ordered by that customer
  - Top 3 dishes highest rated by that customer

For new users or visitors:
  - Global most popular dishes (by reviews)
  - Global top rated dishes
"""

import logging
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Dish, OrderedDish, Order, Account
from app.schemas import HomeResponse, DishResponse
from app.auth import get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/home", tags=["Home"])


def format_cost(cost_cents: int) -> str:
    """Format cost in cents to dollar string"""
    return f"${cost_cents / 100:.2f}"


def dish_to_response(dish: Dish) -> DishResponse:
    """Convert Dish model to DishResponse schema"""
    return DishResponse(
        id=dish.id,
        name=dish.name,
        description=dish.description,
        cost=dish.cost,
        cost_formatted=format_cost(dish.cost),
        picture=dish.picture,
        average_rating=float(dish.average_rating or 0),
        reviews=dish.reviews,
        chefID=dish.chefID,
        restaurantID=dish.restaurantID,
        is_specialty=dish.is_specialty or False
    )


def get_global_popular_dishes(db: Session, limit: int = 3) -> List[Dish]:
    """
    Get globally most popular dishes by reviews count.
    """
    return db.query(Dish).options(
        joinedload(Dish.chef)
    ).order_by(
        desc(Dish.reviews),
        desc(Dish.average_rating)
    ).limit(limit).all()


def get_global_top_rated_dishes(db: Session, limit: int = 3) -> List[Dish]:
    """
    Get globally top-rated dishes.
    Requires minimum review count for quality assurance.
    """
    return db.query(Dish).options(
        joinedload(Dish.chef)
    ).filter(
        Dish.reviews >= 1  # Minimum reviews for quality
    ).order_by(
        desc(Dish.average_rating),
        desc(Dish.reviews)
    ).limit(limit).all()


def get_customer_most_ordered_dishes(db: Session, account_id: int, limit: int = 3) -> List[Dish]:
    """
    Get dishes most ordered by a specific customer.
    """
    # Subquery for order counts per dish
    subquery = db.query(
        OrderedDish.DishID,
        func.sum(OrderedDish.quantity).label('total_ordered')
    ).join(
        Order, OrderedDish.orderID == Order.id
    ).filter(
        Order.accountID == account_id
    ).group_by(
        OrderedDish.DishID
    ).subquery()
    
    # Get dishes with their order counts
    dishes = db.query(Dish).options(
        joinedload(Dish.chef)
    ).join(
        subquery, Dish.id == subquery.c.DishID
    ).order_by(
        desc(subquery.c.total_ordered)
    ).limit(limit).all()
    
    return dishes


def customer_has_order_history(db: Session, account_id: int) -> bool:
    """Check if customer has any completed orders"""
    return db.query(Order).filter(
        Order.accountID == account_id
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
      - Returns top 3 dishes highest rated globally
      
    For new users or visitors:
      - Returns global most popular dishes
      - Returns global top rated dishes
    """
    is_personalized = False
    most_ordered = []
    top_rated = []
    
    # Check if user is logged in and has order history
    if current_user and customer_has_order_history(db, current_user.ID):
        # Personalized recommendations
        is_personalized = True
        
        # Get customer's most ordered dishes
        customer_ordered = get_customer_most_ordered_dishes(db, current_user.ID, limit=3)
        most_ordered = [dish_to_response(d) for d in customer_ordered]
        
        # Get global top rated for top_rated section
        global_rated = get_global_top_rated_dishes(db, limit=3)
        top_rated = [dish_to_response(d) for d in global_rated]
        
        # If not enough personalized results, supplement with global
        if len(most_ordered) < 3:
            existing_ids = {d.id for d in customer_ordered}
            global_popular = get_global_popular_dishes(db, limit=3 - len(most_ordered) + 5)
            for dish in global_popular:
                if dish.id not in existing_ids and len(most_ordered) < 3:
                    most_ordered.append(dish_to_response(dish))
                    existing_ids.add(dish.id)
        
        logger.debug(f"Personalized home for user {current_user.ID}: {len(most_ordered)} ordered, {len(top_rated)} rated")
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
