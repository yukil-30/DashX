"""
Pydantic schemas for request/response validation
"""

from datetime import datetime
from typing import Optional, Literal
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
# Error Schemas
# ============================================================

class ErrorDetail(BaseModel):
    """Standard error response"""
    error: str
    detail: str
    status_code: int
