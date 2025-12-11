"""
Profiles Router
Endpoints for viewing and editing user profiles:
- Customer profiles
- Chef profiles with dishes
- Delivery person profiles with stats
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import get_current_user, get_current_user_optional
from app.models import (
    Account, Dish, Order, OrderedDish, DishReview, OrderDeliveryReview,
    DeliveryRating, AccountProfile
)
from app.schemas import (
    ProfileResponse, ProfileUpdateRequest, ChefProfileResponse,
    DeliveryProfileResponse, DishResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["Profiles"])


def format_cents_to_dollars(cents: int) -> str:
    """Format cents as dollar string"""
    return f"${cents / 100:,.2f}"


def dish_to_response(dish: Dish) -> DishResponse:
    """Convert Dish model to DishResponse schema"""
    return DishResponse(
        id=dish.id,
        name=dish.name,
        description=dish.description,
        cost=dish.cost,
        cost_formatted=format_cents_to_dollars(dish.cost),
        picture=dish.picture,
        average_rating=float(dish.average_rating or 0),
        reviews=dish.reviews,
        chefID=dish.chefID,
        restaurantID=dish.restaurantID
    )


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """Get the current user's profile"""
    return await get_profile_by_id(current_user.ID, db)


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    update_data: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user)
):
    """Update the current user's profile"""
    # Get or create profile
    profile = db.query(AccountProfile).filter(
        AccountProfile.account_id == current_user.ID
    ).first()
    
    if not profile:
        profile = AccountProfile(
            account_id=current_user.ID,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        db.add(profile)
    
    # Update fields
    if update_data.display_name is not None:
        profile.display_name = update_data.display_name
    if update_data.bio is not None:
        profile.bio = update_data.bio
    if update_data.phone is not None:
        profile.phone = update_data.phone
    if update_data.address is not None:
        profile.address = update_data.address
    if update_data.specialty is not None and current_user.type == 'chef':
        profile.specialty = update_data.specialty
    
    profile.updated_at = datetime.now(timezone.utc).isoformat()
    
    db.commit()
    db.refresh(profile)
    
    return await get_profile_by_id(current_user.ID, db)


@router.get("/users/{user_id}", response_model=ProfileResponse)
async def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get a user's public profile"""
    return await get_profile_by_id(user_id, db)


async def get_profile_by_id(user_id: int, db: Session) -> ProfileResponse:
    """Helper to get profile by user ID"""
    account = db.query(Account).filter(Account.ID == user_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get profile if exists
    profile = db.query(AccountProfile).filter(
        AccountProfile.account_id == user_id
    ).first()
    
    # Get order stats
    total_orders = db.query(Order).filter(Order.accountID == user_id).count()
    
    # Get review stats
    reviews_given = db.query(DishReview).filter(
        DishReview.account_id == user_id
    ).all()
    total_reviews = len(reviews_given)
    avg_rating_given = sum(r.rating for r in reviews_given) / total_reviews if reviews_given else 0
    
    # Chef stats
    dishes_created = 0
    avg_dish_rating = 0.0
    if account.type == 'chef':
        chef_dishes = db.query(Dish).filter(Dish.chefID == user_id).all()
        dishes_created = len(chef_dishes)
        if chef_dishes:
            total_rating = sum(float(d.average_rating or 0) for d in chef_dishes)
            avg_dish_rating = total_rating / dishes_created if dishes_created else 0
    
    # Delivery stats
    total_deliveries = 0
    avg_delivery_rating = 0.0
    on_time_pct = 0.0
    if account.type == 'delivery':
        delivery_rating = db.query(DeliveryRating).filter(
            DeliveryRating.accountID == user_id
        ).first()
        if delivery_rating:
            total_deliveries = delivery_rating.total_deliveries
            avg_delivery_rating = float(delivery_rating.averageRating or 0)
            on_time_pct = (delivery_rating.on_time_deliveries / total_deliveries * 100) if total_deliveries else 0
    
    return ProfileResponse(
        account_id=account.ID,
        email=account.email,
        account_type=account.type,
        warnings=account.warnings,
        customer_tier=account.customer_tier,
        display_name=profile.display_name if profile else None,
        bio=profile.bio if profile else None,
        profile_picture=profile.profile_picture if profile else None,
        phone=profile.phone if profile else None,
        address=profile.address if profile else None,
        specialty=profile.specialty if profile else None,
        created_at=profile.created_at if profile else None,
        total_orders=total_orders,
        total_reviews_given=total_reviews,
        average_rating_given=avg_rating_given,
        dishes_created=dishes_created,
        average_dish_rating=avg_dish_rating,
        total_deliveries=total_deliveries,
        average_delivery_rating=avg_delivery_rating,
        on_time_percentage=on_time_pct
    )


@router.get("/chefs", response_model=list[ChefProfileResponse])
async def list_chefs(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """List all chef profiles"""
    offset = (page - 1) * per_page
    
    chefs = db.query(Account).filter(
        Account.type == 'chef'
    ).offset(offset).limit(per_page).all()
    
    result = []
    for chef in chefs:
        profile = db.query(AccountProfile).filter(
            AccountProfile.account_id == chef.ID
        ).first()
        
        dishes = db.query(Dish).filter(Dish.chefID == chef.ID).all()
        dishes_response = [dish_to_response(d) for d in dishes]
        
        avg_rating = 0.0
        if dishes:
            total = sum(float(d.average_rating or 0) for d in dishes)
            avg_rating = total / len(dishes)
        
        result.append(ChefProfileResponse(
            account_id=chef.ID,
            email=chef.email,
            account_type=chef.type,
            display_name=profile.display_name if profile else None,
            bio=profile.bio if profile else None,
            profile_picture=profile.profile_picture if profile else "/images/chef-placeholder.svg",
            specialty=profile.specialty if profile else None,
            dishes_created=len(dishes),
            average_dish_rating=avg_rating,
            dishes=dishes_response
        ))
    
    return result


@router.get("/chefs/{chef_id}", response_model=ChefProfileResponse)
async def get_chef_profile(
    chef_id: int,
    db: Session = Depends(get_db)
):
    """Get a chef's profile with their dishes"""
    chef = db.query(Account).filter(
        Account.ID == chef_id,
        Account.type == 'chef'
    ).first()
    
    if not chef:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chef not found"
        )
    
    profile = db.query(AccountProfile).filter(
        AccountProfile.account_id == chef_id
    ).first()
    
    dishes = db.query(Dish).filter(Dish.chefID == chef_id).all()
    dishes_response = [dish_to_response(d) for d in dishes]
    
    avg_rating = 0.0
    if dishes:
        total = sum(float(d.average_rating or 0) for d in dishes)
        avg_rating = total / len(dishes)
    
    return ChefProfileResponse(
        account_id=chef.ID,
        email=chef.email,
        account_type=chef.type,
        display_name=profile.display_name if profile else None,
        bio=profile.bio if profile else None,
        profile_picture=profile.profile_picture if profile else "/images/chef-placeholder.svg",
        specialty=profile.specialty if profile else None,
        dishes_created=len(dishes),
        average_dish_rating=avg_rating,
        dishes=dishes_response
    )


@router.get("/delivery", response_model=list[DeliveryProfileResponse])
async def list_delivery_persons(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """List all delivery person profiles"""
    offset = (page - 1) * per_page
    
    delivery_persons = db.query(Account).filter(
        Account.type == 'delivery'
    ).offset(offset).limit(per_page).all()
    
    result = []
    for dp in delivery_persons:
        profile = db.query(AccountProfile).filter(
            AccountProfile.account_id == dp.ID
        ).first()
        
        rating = db.query(DeliveryRating).filter(
            DeliveryRating.accountID == dp.ID
        ).first()
        
        on_time_pct = 0.0
        if rating and rating.total_deliveries:
            on_time_pct = (rating.on_time_deliveries / rating.total_deliveries * 100)
        
        result.append(DeliveryProfileResponse(
            account_id=dp.ID,
            email=dp.email,
            account_type=dp.type,
            display_name=profile.display_name if profile else None,
            bio=profile.bio if profile else None,
            profile_picture=profile.profile_picture if profile else "/images/delivery-placeholder.svg",
            total_deliveries=rating.total_deliveries if rating else 0,
            on_time_deliveries=rating.on_time_deliveries if rating else 0,
            average_delivery_rating=float(rating.averageRating or 0) if rating else 0.0,
            on_time_percentage=on_time_pct
        ))
    
    return result


@router.get("/delivery/{delivery_id}", response_model=DeliveryProfileResponse)
async def get_delivery_profile(
    delivery_id: int,
    db: Session = Depends(get_db)
):
    """Get a delivery person's profile"""
    dp = db.query(Account).filter(
        Account.ID == delivery_id,
        Account.type == 'delivery'
    ).first()
    
    if not dp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery person not found"
        )
    
    profile = db.query(AccountProfile).filter(
        AccountProfile.account_id == delivery_id
    ).first()
    
    rating = db.query(DeliveryRating).filter(
        DeliveryRating.accountID == delivery_id
    ).first()
    
    on_time_pct = 0.0
    if rating and rating.total_deliveries:
        on_time_pct = (rating.on_time_deliveries / rating.total_deliveries * 100)
    
    return DeliveryProfileResponse(
        account_id=dp.ID,
        email=dp.email,
        account_type=dp.type,
        display_name=profile.display_name if profile else None,
        bio=profile.bio if profile else None,
        profile_picture=profile.profile_picture if profile else "/images/delivery-placeholder.svg",
        total_deliveries=rating.total_deliveries if rating else 0,
        on_time_deliveries=rating.on_time_deliveries if rating else 0,
        average_delivery_rating=float(rating.averageRating or 0) if rating else 0.0,
        on_time_percentage=on_time_pct
    )
