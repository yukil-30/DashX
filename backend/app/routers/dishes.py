"""
Dishes Router - CRUD operations for menu items
Includes:
- GET /dishes - List/search dishes with pagination
- GET /dishes/{id} - Get single dish
- POST /dishes - Create dish (chef-only)
- PUT /dishes/{id} - Update dish (chef-only)
- DELETE /dishes/{id} - Delete dish (chef-only)
- POST /dishes/{id}/rate - Rate a dish
"""

import logging
from typing import Optional, Literal
from decimal import Decimal


from fastapi import File, UploadFile, Form
import shutil
import time
import os
import json

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Dish, Account, OrderedDish, Order
from app.schemas import (
    DishCreateRequest, DishUpdateRequest, DishResponse, DishListResponse,
    DishRateRequest, DishRateResponse
)
from app.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dishes", tags=["Dishes"])


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
        restaurantID=dish.restaurantID
    )


@router.get("", response_model=DishListResponse)
async def list_dishes(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    q: Optional[str] = Query(None, max_length=100, description="Search query for dish name"),
    chef_id: Optional[int] = Query(None, description="Filter by chef ID"),
    order_by: Literal["popular", "rating", "cost", "newest"] = Query(
        "popular", 
        description="Sort order: popular, rating, cost, newest"
    ),
    db: Session = Depends(get_db)
):
    """
    List dishes with pagination, search, and filtering.
    """
    # Build base query
    query = db.query(Dish).options(
        joinedload(Dish.chef)
    )
    
    if chef_id:
        query = query.filter(Dish.chefID == chef_id)
    
    # Search by name (case-insensitive)
    if q:
        search_term = f"%{q}%"
        query = query.filter(Dish.name.ilike(search_term))
    
    # Apply ordering
    if order_by == "popular":
        query = query.order_by(desc(Dish.reviews), desc(Dish.average_rating))
    elif order_by == "rating":
        query = query.order_by(desc(Dish.average_rating), desc(Dish.reviews))
    elif order_by == "cost":
        query = query.order_by(asc(Dish.cost))
    elif order_by == "newest":
        query = query.order_by(desc(Dish.id))
    
    # Get total count
    total = query.count()
    
    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page
    offset = (page - 1) * per_page
    
    # Fetch dishes
    dishes = query.offset(offset).limit(per_page).all()
    
    return DishListResponse(
        dishes=[dish_to_response(d) for d in dishes],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/{dish_id}", response_model=DishResponse)
async def get_dish(
    dish_id: int,
    db: Session = Depends(get_db)
):
    """Get a single dish by ID"""
    dish = db.query(Dish).options(
        joinedload(Dish.chef)
    ).filter(Dish.id == dish_id).first()
    
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        )
    
    return dish_to_response(dish)


@router.post("", response_model=DishResponse, status_code=status.HTTP_201_CREATED)
async def create_dish(
    dish_data: str = Form(...),                 # ⬅ CHANGED
    image: UploadFile | None = File(None),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new dish (chef-only).
    """

    # Convert JSON string from FormData → Pydantic model
    dish_data = DishCreateRequest(**json.loads(dish_data))   # ⬅ ADDED

    # Validate name - prevent XSS
    name = dish_data.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Dish name cannot be empty"
        )
    if "<" in name or ">" in name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Dish name cannot contain HTML characters"
        )
    
    # Check chef permission
    if current_user.type not in ["chef", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only chefs and managers can create dishes"
        )
    
    # Get restaurant_id (use first restaurant if not assigned)
    restaurant_id = current_user.restaurantID
    if not restaurant_id:
        restaurant_id = 1
        
    # Handle image upload
    image_path = None
    if image:
        filename = f"{int(time.time())}_{image.filename}"
        save_path = os.path.join("static", filename)

        # Ensure folder exists
        os.makedirs("static", exist_ok=True)

        # Save file
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # URL path returned to frontend
        image_path = f"/static/{filename}"

    # Create dish
    dish = Dish(
        restaurantID=restaurant_id,
        chefID=current_user.ID,
        name=name,
        description=dish_data.description,
        cost=dish_data.cost,   # already in cents
        picture=image_path,
        average_rating=Decimal("0.00"),
        reviews=0
    )

    db.add(dish)
    db.commit()
    db.refresh(dish)
    
    logger.info(f"Dish created: {dish.id} - {dish.name} by chef {current_user.ID}")
    
    return dish_to_response(dish)


@router.put("/{dish_id}", response_model=DishResponse)
async def update_dish(
    dish_id: int,
    update_data: DishUpdateRequest,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a dish (chef-only).
    
    Only the chef who created the dish or a manager can update it.
    """
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        )
    
    # Check permission
    if current_user.type == "manager":
        pass  # Managers can update any dish
    elif current_user.type == "chef":
        if dish.chefID != current_user.ID:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own dishes"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only chefs and managers can update dishes"
        )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(dish, field, value)
    
    db.commit()
    db.refresh(dish)
    
    logger.info(f"Dish updated: {dish.id} by user {current_user.ID}")
    
    return dish_to_response(dish)


@router.delete("/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dish(
    dish_id: int,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a dish (chef-only).
    
    Only the chef who created the dish or a manager can delete it.
    """
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        )
    
    # Check permission
    if current_user.type == "manager":
        pass  # Managers can delete any dish
    elif current_user.type == "chef":
        if dish.chefID != current_user.ID:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own dishes"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only chefs and managers can delete dishes"
        )
    
    db.delete(dish)
    db.commit()
    
    logger.info(f"Dish deleted: {dish_id} by user {current_user.ID}")
    
    return None


@router.post("/{dish_id}/rate", response_model=DishRateResponse)
async def rate_dish(
    dish_id: int,
    rate_request: DishRateRequest,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rate a dish (must have ordered it).
    
    Validates that:
    1. The dish exists
    2. The order exists and belongs to the user
    3. The order contains the dish
    
    Updates denormalized rating fields on the dish.
    """
    # Check dish exists
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        )
    
    # Check order exists and belongs to user
    order = db.query(Order).filter(
        Order.id == rate_request.order_id,
        Order.accountID == current_user.ID
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or doesn't belong to you"
        )
    
    # Check order contains this dish
    ordered_dish = db.query(OrderedDish).filter(
        OrderedDish.orderID == rate_request.order_id,
        OrderedDish.DishID == dish_id
    ).first()
    
    if not ordered_dish:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This dish was not part of the specified order"
        )
    
    # Update denormalized rating on dish
    # Formula: new_avg = (old_avg * old_count + new_rating) / (old_count + 1)
    old_avg = float(dish.average_rating or 0)
    old_count = dish.reviews
    new_count = old_count + 1
    new_avg = (old_avg * old_count + rate_request.rating) / new_count
    
    dish.average_rating = Decimal(str(round(new_avg, 2)))
    dish.reviews = new_count
    
    db.commit()
    
    logger.info(f"Dish {dish_id} rated {rate_request.rating} by user {current_user.ID}")
    
    return DishRateResponse(
        message="Rating submitted successfully",
        new_average_rating=float(dish.average_rating),
        reviews=dish.reviews
    )
