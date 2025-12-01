"""
Pydantic schemas for request/response validation
"""

from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============================================================
# Auth Schemas
# ============================================================

class UserRegisterRequest(BaseModel):
    """Registration request schema"""
    username: EmailStr = Field(..., description="Email address (used as username)")
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 chars)")
    display_name: str = Field(..., min_length=1, max_length=200, description="Display name")
    email: EmailStr = Field(..., description="Email address")
    role_requested: Literal["customer", "visitor"] = Field(
        default="customer",
        description="Role to register as (customer or visitor only)"
    )
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Ensure password meets complexity requirements"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class UserLoginRequest(BaseModel):
    """Login request schema"""
    username: str = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiry in seconds")


class UserProfile(BaseModel):
    """User profile response (no sensitive data)"""
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    account_type: str
    balance_cents: int = Field(..., description="Account balance in cents")
    warnings: int = 0
    is_blacklisted: bool = False
    free_delivery_credits: int = 0
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    """User profile API response"""
    user: UserProfile


# ============================================================
# Account Schemas
# ============================================================

class DepositRequest(BaseModel):
    """Deposit request schema"""
    amount_cents: int = Field(..., gt=0, le=1_000_000_00, description="Amount to deposit in cents (must be positive, max $1M)")


class BalanceResponse(BaseModel):
    """Balance response schema"""
    balance_cents: int = Field(..., description="Current balance in cents")
    balance_formatted: str = Field(..., description="Formatted balance (e.g., $10.50)")


class DepositResponse(BaseModel):
    """Deposit response schema"""
    message: str
    new_balance_cents: int
    new_balance_formatted: str
    transaction_id: int


# ============================================================
# Dish Schemas
# ============================================================

class DishImageResponse(BaseModel):
    """Dish image response schema"""
    id: int
    image_url: str
    display_order: int

    class Config:
        from_attributes = True


class DishBase(BaseModel):
    """Base dish schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Dish name")
    description: Optional[str] = Field(None, max_length=2000, description="Dish description")
    price_cents: int = Field(..., gt=0, le=100_000_00, description="Price in cents (max $1000)")
    category: Optional[str] = Field(None, max_length=100, description="Dish category")
    is_available: bool = Field(True, description="Whether dish is available for order")
    is_special: bool = Field(False, description="Whether dish is a daily special")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Clean and validate dish name"""
        v = v.strip()
        if not v:
            raise ValueError("Dish name cannot be empty")
        # Remove potentially dangerous characters
        if "<" in v or ">" in v:
            raise ValueError("Dish name cannot contain HTML characters")
        return v
    
    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Clean description"""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class DishCreateRequest(DishBase):
    """Request schema for creating a dish (without images - those come via multipart)"""
    pass


class DishUpdateRequest(BaseModel):
    """Request schema for updating a dish (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    price_cents: Optional[int] = Field(None, gt=0, le=100_000_00)
    category: Optional[str] = Field(None, max_length=100)
    is_available: Optional[bool] = None
    is_special: Optional[bool] = None


class DishResponse(BaseModel):
    """Full dish response with all details"""
    id: int
    name: str
    description: Optional[str]
    price_cents: int
    price_formatted: str
    category: Optional[str]
    is_available: bool
    is_special: bool
    average_rating: float
    review_count: int
    order_count: int
    chef_id: Optional[int]
    chef_name: Optional[str] = None
    images: List[DishImageResponse] = []
    picture: Optional[str] = None  # Main image URL
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DishListResponse(BaseModel):
    """Paginated dish list response"""
    dishes: List[DishResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class DishRateRequest(BaseModel):
    """Request schema for rating a dish"""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5 stars")
    order_id: int = Field(..., description="Order ID that included this dish")
    review_text: Optional[str] = Field(None, max_length=2000, description="Optional review text")


class DishRateResponse(BaseModel):
    """Response after rating a dish"""
    message: str
    new_average_rating: float
    review_count: int


# ============================================================
# Home/Personalization Schemas
# ============================================================

class HomeResponse(BaseModel):
    """Personalized home page response"""
    most_ordered: List[DishResponse] = Field(
        default_factory=list,
        description="Top dishes by order count (personalized or global)"
    )
    top_rated: List[DishResponse] = Field(
        default_factory=list,
        description="Top dishes by rating (personalized or global)"
    )
    is_personalized: bool = Field(
        default=False,
        description="Whether results are personalized for the user"
    )


# ============================================================
# Error Schemas
# ============================================================

class ErrorDetail(BaseModel):
    """Standard error response"""
    error: str
    detail: str
    status_code: int
