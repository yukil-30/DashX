"""
Authentication Router
Endpoints for user registration, login, and profile management
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Account, Blacklist, Restaurant
from app.schemas import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    UserProfile, UserProfileResponse, TokenResponseWithWarnings, LoginWarningInfo,
    ManagerRegisterRequest
)
from app.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    Only 'customer' and 'visitor' roles can be self-registered.
    Employee roles (chef, delivery, manager) require manager approval via openRequest.
    
    Returns a JWT access token upon successful registration.
    """
    # Check if email already exists
    existing_user = db.query(Account).filter(Account.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create new user with schema fields
    try:
        new_user = Account(
            email=request.email,
            password=hash_password(request.password),
            type=request.type,
            balance=0,
            warnings=0
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New user registered: {new_user.email} as {new_user.type}")
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Generate access token
    access_token = create_access_token(
        data={"sub": new_user.email, "user_id": new_user.ID, "role": new_user.type}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/register-manager", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_manager(
    request: ManagerRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new manager account and create a new restaurant.
    
    This endpoint creates a new restaurant and assigns the manager to it.
    Returns a JWT access token upon successful registration.
    """
    # Check if email already exists
    existing_user = db.query(Account).filter(Account.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    try:
        # Create restaurant first
        new_restaurant = Restaurant(
            name=request.restaurant_name.strip()
        )
        db.add(new_restaurant)
        db.flush()  # Get the restaurant ID without committing
        
        # Create manager account linked to the restaurant
        new_user = Account(
            email=request.email,
            password=hash_password(request.password),
            type="manager",
            balance=0,
            warnings=0,
            restaurantID=new_restaurant.id
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New manager registered: {new_user.email} for restaurant: {new_restaurant.name} (ID: {new_restaurant.id})")
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered or restaurant name taken"
        )
    
    # Generate access token
    access_token = create_access_token(
        data={"sub": new_user.email, "user_id": new_user.ID, "role": new_user.type}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/login", response_model=TokenResponseWithWarnings)
async def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT access token.
    Also returns warning information if the user has any warnings.
    """
    # Check if email is blacklisted
    blacklisted = db.query(Blacklist).filter(Blacklist.email == request.email).first()
    if blacklisted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been permanently suspended",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Find user by email
    user = db.query(Account).filter(Account.email == request.email).first()
    
    if not user:
        # Use same error message to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if user is blacklisted
    if user.is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been permanently suspended",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if employee is fired
    if user.is_fired:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This employee account has been terminated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verify password
    if not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    logger.info(f"User logged in: {user.email}")
    
    # Generate access token
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.ID, "role": user.type}
    )
    
    # Build warning info
    warning_info = None
    if user.warnings > 0:
        # Determine thresholds based on user type
        if user.type == "vip":
            threshold = 2
            is_near = user.warnings >= 1
        elif user.type in ["customer", "visitor"]:
            threshold = 3
            is_near = user.warnings >= 2
        else:
            threshold = None
            is_near = False
        
        if threshold:
            warning_message = f"You have {user.warnings} warning(s). "
            if user.warnings >= threshold - 1:
                if user.type == "vip":
                    warning_message += "One more warning will result in VIP status removal."
                else:
                    warning_message += "Reaching 3 warnings will result in account suspension."
            
            warning_info = LoginWarningInfo(
                warnings_count=user.warnings,
                warning_message=warning_message,
                is_near_threshold=is_near
            )
    
    return TokenResponseWithWarnings(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        warning_info=warning_info
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: Account = Depends(get_current_user)
):
    """
    Get the current authenticated user's profile.
    
    Requires valid JWT token in Authorization header.
    """
    profile = UserProfile(
        ID=current_user.ID,
        email=current_user.email,
        type=current_user.type,
        balance=current_user.balance,
        warnings=current_user.warnings,
        wage=current_user.wage,
        restaurantID=current_user.restaurantID
    )
    
    return UserProfileResponse(user=profile)


@router.post("/logout")
async def logout(current_user: Account = Depends(get_current_user)):
    """
    Logout endpoint.
    
    Note: With stateless JWT tokens, true logout requires client-side token deletion.
    For production, implement a token blacklist using Redis or database.
    
    This endpoint serves as a confirmation that the user intends to logout.
    """
    logger.info(f"User logged out: {current_user.email}")
    
    return {
        "message": "Successfully logged out",
        "detail": "Please delete the access token on your client"
    }
