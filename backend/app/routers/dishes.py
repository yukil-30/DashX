"""
Dishes Router - CRUD operations for menu items
Includes:
- GET /dishes - List/search dishes with pagination
- GET /dishes/{id} - Get single dish
- POST /dishes - Create dish (chef-only) with image upload
- PUT /dishes/{id} - Update dish (chef-only)
- DELETE /dishes/{id} - Delete dish (chef-only)
- POST /dishes/{id}/rate - Rate a dish
- POST /dishes/{id}/images - Add images to a dish
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional, List, Literal
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Dish, DishImage, DishReview, Account, OrderedDish, Order
from app.schemas import (
    DishCreateRequest, DishUpdateRequest, DishResponse, DishListResponse,
    DishRateRequest, DishRateResponse, DishImageResponse
)
from app.auth import get_current_user, get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dishes", tags=["Dishes"])

# Static images directory
STATIC_IMAGES_DIR = Path("/app/static/images")
STATIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Allowed image types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def format_price(price_cents: int) -> str:
    """Format price in cents to dollar string"""
    return f"${price_cents / 100:.2f}"


def dish_to_response(dish: Dish, include_chef_name: bool = True) -> DishResponse:
    """Convert Dish model to DishResponse schema"""
    chef_name = None
    if include_chef_name and dish.chef:
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
        images=[DishImageResponse.model_validate(img) for img in dish.images],
        picture=dish.picture,
        created_at=dish.created_at,
        updated_at=dish.updated_at
    )


async def save_uploaded_image(file: UploadFile) -> str:
    """
    Save an uploaded image file and return its URL path.
    Validates file type and size.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    # Read file content
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image too large. Maximum size: {MAX_IMAGE_SIZE // 1024 // 1024}MB"
        )
    
    # Generate unique filename
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = STATIC_IMAGES_DIR / filename
    
    # Save file
    with open(filepath, 'wb') as f:
        f.write(content)
    
    # Return URL path (relative to static)
    return f"/static/images/{filename}"


@router.get("", response_model=DishListResponse)
async def list_dishes(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    q: Optional[str] = Query(None, max_length=100, description="Search query for dish name"),
    chef_id: Optional[int] = Query(None, description="Filter by chef ID"),
    category: Optional[str] = Query(None, max_length=100, description="Filter by category"),
    order_by: Literal["popular", "rating", "price", "newest"] = Query(
        "popular", 
        description="Sort order: popular (order_count), rating, price, newest"
    ),
    available_only: bool = Query(True, description="Only show available dishes"),
    db: Session = Depends(get_db)
):
    """
    List dishes with pagination, search, and filtering.
    
    Supports:
    - Text search on dish name (uses trigram similarity if available)
    - Filter by chef_id
    - Filter by category
    - Sort by popularity, rating, price, or newest
    """
    # Build base query
    query = db.query(Dish).options(
        joinedload(Dish.chef),
        joinedload(Dish.images)
    )
    
    # Apply filters
    if available_only:
        query = query.filter(Dish.is_available == True)
    
    if chef_id:
        query = query.filter(Dish.chef_id == chef_id)
    
    if category:
        query = query.filter(func.lower(Dish.category) == category.lower())
    
    # Search by name (case-insensitive, uses trigram if available)
    if q:
        search_term = f"%{q}%"
        query = query.filter(Dish.name.ilike(search_term))
    
    # Apply ordering
    if order_by == "popular":
        query = query.order_by(desc(Dish.order_count), desc(Dish.average_rating))
    elif order_by == "rating":
        query = query.order_by(desc(Dish.average_rating), desc(Dish.review_count))
    elif order_by == "price":
        query = query.order_by(asc(Dish.price))
    elif order_by == "newest":
        query = query.order_by(desc(Dish.created_at))
    
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
        joinedload(Dish.chef),
        joinedload(Dish.images)
    ).filter(Dish.id == dish_id).first()
    
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        )
    
    return dish_to_response(dish)


@router.post("", response_model=DishResponse, status_code=status.HTTP_201_CREATED)
async def create_dish(
    name: str = Form(..., min_length=1, max_length=255),
    description: Optional[str] = Form(None),
    price_cents: int = Form(..., gt=0),
    category: Optional[str] = Form(None),
    is_available: bool = Form(True),
    is_special: bool = Form(False),
    images: List[UploadFile] = File(default=[]),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new dish (chef-only).
    
    Supports multipart form data with multiple image uploads.
    Images are saved to backend/static/images/ directory.
    """
    # Validate name - prevent XSS
    name = name.strip()
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
    
    # Clean description
    if description:
        description = description.strip() or None
    
    # Check chef permission
    if current_user.account_type not in ["chef", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only chefs and managers can create dishes"
        )
    
    # Get restaurant_id (use first restaurant if not assigned)
    restaurant_id = current_user.restaurant_id
    if not restaurant_id:
        # Use default restaurant (ID 1)
        restaurant_id = 1
    
    # Create dish
    dish = Dish(
        restaurant_id=restaurant_id,
        chef_id=current_user.id,
        name=name,
        description=description,
        price=price_cents,
        category=category,
        is_available=is_available,
        is_special=is_special,
        average_rating=Decimal("0.00"),
        review_count=0,
        order_count=0
    )
    db.add(dish)
    db.flush()  # Get the dish ID
    
    # Save images
    image_urls = []
    for idx, image_file in enumerate(images):
        if image_file.filename:  # Skip empty file inputs
            url = await save_uploaded_image(image_file)
            image_urls.append(url)
            
            dish_image = DishImage(
                dish_id=dish.id,
                image_url=url,
                display_order=idx
            )
            db.add(dish_image)
    
    # Set first image as main picture
    if image_urls:
        dish.picture = image_urls[0]
    
    db.commit()
    db.refresh(dish)
    
    logger.info(f"Dish created: {dish.id} - {dish.name} by chef {current_user.id}")
    
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
    if current_user.account_type == "manager":
        pass  # Managers can update any dish
    elif current_user.account_type == "chef":
        if dish.chef_id != current_user.id:
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
    if "price_cents" in update_dict:
        update_dict["price"] = update_dict.pop("price_cents")
    
    for field, value in update_dict.items():
        setattr(dish, field, value)
    
    db.commit()
    db.refresh(dish)
    
    logger.info(f"Dish updated: {dish.id} by user {current_user.id}")
    
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
    Soft-delete by setting is_available=False could be an alternative.
    """
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        )
    
    # Check permission
    if current_user.account_type == "manager":
        pass  # Managers can delete any dish
    elif current_user.account_type == "chef":
        if dish.chef_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own dishes"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only chefs and managers can delete dishes"
        )
    
    # Delete associated images from disk
    for img in dish.images:
        if img.image_url.startswith("/static/images/"):
            filepath = Path("/app") / img.image_url.lstrip("/")
            if filepath.exists():
                try:
                    filepath.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete image file {filepath}: {e}")
    
    db.delete(dish)
    db.commit()
    
    logger.info(f"Dish deleted: {dish_id} by user {current_user.id}")
    
    return None


@router.post("/{dish_id}/images", response_model=List[DishImageResponse])
async def add_dish_images(
    dish_id: int,
    images: List[UploadFile] = File(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add images to an existing dish (chef-only)"""
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        )
    
    # Check permission
    if current_user.account_type not in ["chef", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only chefs and managers can add images"
        )
    
    if current_user.account_type == "chef" and dish.chef_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add images to your own dishes"
        )
    
    # Get current max display order
    max_order = db.query(func.max(DishImage.display_order)).filter(
        DishImage.dish_id == dish_id
    ).scalar() or -1
    
    # Save new images
    new_images = []
    for idx, image_file in enumerate(images):
        if image_file.filename:
            url = await save_uploaded_image(image_file)
            dish_image = DishImage(
                dish_id=dish.id,
                image_url=url,
                display_order=max_order + idx + 1
            )
            db.add(dish_image)
            new_images.append(dish_image)
    
    # Update main picture if none exists
    if not dish.picture and new_images:
        dish.picture = new_images[0].image_url
    
    db.commit()
    
    return [DishImageResponse.model_validate(img) for img in new_images]


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
    4. User hasn't already rated this dish for this order
    
    Efficiently updates denormalized rating fields on the dish.
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
        Order.account_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or doesn't belong to you"
        )
    
    # Check order contains this dish
    ordered_dish = db.query(OrderedDish).filter(
        OrderedDish.order_id == rate_request.order_id,
        OrderedDish.dish_id == dish_id
    ).first()
    
    if not ordered_dish:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This dish was not part of the specified order"
        )
    
    # Check for existing review
    existing_review = db.query(DishReview).filter(
        DishReview.dish_id == dish_id,
        DishReview.account_id == current_user.id,
        DishReview.order_id == rate_request.order_id
    ).first()
    
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already rated this dish for this order"
        )
    
    # Create review
    review = DishReview(
        dish_id=dish_id,
        account_id=current_user.id,
        order_id=rate_request.order_id,
        rating=rate_request.rating,
        review_text=rate_request.review_text
    )
    db.add(review)
    
    # Update denormalized rating on dish
    # Formula: new_avg = (old_avg * old_count + new_rating) / (old_count + 1)
    old_avg = float(dish.average_rating or 0)
    old_count = dish.review_count
    new_count = old_count + 1
    new_avg = (old_avg * old_count + rate_request.rating) / new_count
    
    dish.average_rating = Decimal(str(round(new_avg, 2)))
    dish.review_count = new_count
    
    db.commit()
    
    logger.info(f"Dish {dish_id} rated {rate_request.rating} by user {current_user.id}")
    
    return DishRateResponse(
        message="Rating submitted successfully",
        new_average_rating=float(dish.average_rating),
        review_count=dish.review_count
    )
