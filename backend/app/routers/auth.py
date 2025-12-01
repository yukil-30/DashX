"""
Authentication Router
Endpoints for user registration, login, and profile management
"""

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Account
from app.schemas import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    UserProfile, UserProfileResponse
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
    Employee roles (chef, delivery, manager) require manager approval.
    
    Returns a JWT access token upon successful registration.
    """
    # Check if email already exists
    existing_user = db.query(Account).filter(Account.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Also check username if different from email (username is email in our system)
    if request.username != request.email:
        existing_username = db.query(Account).filter(Account.email == request.username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered"
            )
    
    # Parse display name into first/last name
    name_parts = request.display_name.strip().split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else None
    
    # Create new user
    try:
        new_user = Account(
            email=request.email,
            password_hash=hash_password(request.password),
            first_name=first_name,
            last_name=last_name,
            account_type=request.role_requested,
            balance=0,
            warnings=0,
            is_blacklisted=False,
            free_delivery_credits=0,
            created_at=datetime.now(timezone.utc),
            last_login_at=datetime.now(timezone.utc)
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New user registered: {new_user.email} as {new_user.account_type}")
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Generate access token
    access_token = create_access_token(
        data={"sub": new_user.email, "user_id": new_user.id, "role": new_user.account_type}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT access token.
    
    Username is the user's email address.
    """
    # Find user by email (username is email)
    user = db.query(Account).filter(Account.email == request.username).first()
    
    if not user:
        # Use same error message to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if user is blacklisted
    if user.is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended"
        )
    
    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    
    logger.info(f"User logged in: {user.email}")
    
    # Generate access token
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "role": user.account_type}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: Account = Depends(get_current_user)
):
    """
    Get the current authenticated user's profile.
    
    Requires valid JWT token in Authorization header.
    """
    # Build display name from first/last name
    display_name = current_user.first_name or ""
    if current_user.last_name:
        display_name = f"{display_name} {current_user.last_name}".strip()
    
    profile = UserProfile(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        display_name=display_name if display_name else current_user.email,
        account_type=current_user.account_type,
        balance_cents=current_user.balance,
        warnings=current_user.warnings,
        is_blacklisted=current_user.is_blacklisted,
        free_delivery_credits=current_user.free_delivery_credits,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at
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
