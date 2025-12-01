"""
Pydantic schemas for request/response validation
Matches exactly the authoritative database schema.
"""

from typing import Optional, Literal, List
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============================================================
# Auth Schemas
# ============================================================

class UserRegisterRequest(BaseModel):
    """Registration request schema"""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 chars)")
    type: Literal["customer", "visitor"] = Field(
        default="customer",
        description="Account type (customer or visitor only for self-registration)"
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
    email: str = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiry in seconds")


class UserProfile(BaseModel):
    """User profile response (no sensitive data)"""
    ID: int
    email: str
    type: str
    balance: int = Field(..., description="Account balance in cents")
    warnings: int = 0
    wage: Optional[int] = None
    restaurantID: Optional[int] = None

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


# ============================================================
# Dish Schemas
# ============================================================

class DishBase(BaseModel):
    """Base dish schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Dish name")
    description: Optional[str] = Field(None, max_length=2000, description="Dish description")
    cost: int = Field(..., gt=0, le=100_000_00, description="Cost in cents (max $1000)")
    
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
    """Request schema for creating a dish"""
    pass


class DishUpdateRequest(BaseModel):
    """Request schema for updating a dish (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    cost: Optional[int] = Field(None, gt=0, le=100_000_00)
    picture: Optional[str] = None


class DishResponse(BaseModel):
    """Full dish response with all details"""
    id: int
    name: str
    description: Optional[str]
    cost: int
    cost_formatted: str
    picture: Optional[str] = None
    average_rating: float
    reviews: int
    chefID: Optional[int]
    restaurantID: int

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


class DishRateResponse(BaseModel):
    """Response after rating a dish"""
    message: str
    new_average_rating: float
    reviews: int


# ============================================================
# Order Schemas
# ============================================================

class OrderItemRequest(BaseModel):
    """Request for a single item in an order"""
    dish_id: int = Field(..., description="Dish ID")
    qty: int = Field(..., gt=0, description="Quantity")


class OrderCreateRequest(BaseModel):
    """Request schema for creating an order"""
    items: List[OrderItemRequest] = Field(..., min_length=1, description="List of items to order")
    delivery_address: str = Field(..., min_length=1, max_length=500, description="Delivery address")
    note: Optional[str] = Field(None, max_length=500)


class OrderedDishRequest(BaseModel):
    """Request for adding a dish to an order"""
    DishID: int
    quantity: int = Field(..., gt=0)


class OrderedDishResponse(BaseModel):
    """Response for an ordered dish"""
    DishID: int
    quantity: int
    dish_name: Optional[str] = None
    dish_cost: Optional[int] = None

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Order response schema"""
    id: int
    accountID: int
    dateTime: Optional[str]
    finalCost: int
    status: str
    bidID: Optional[int]
    note: Optional[str]
    delivery_address: Optional[str]
    delivery_fee: int
    subtotal_cents: int
    discount_cents: int
    free_delivery_used: int
    ordered_dishes: List[OrderedDishResponse] = []

    class Config:
        from_attributes = True


class OrderCreateResponse(BaseModel):
    """Response after successfully creating an order"""
    message: str
    order: OrderResponse
    balance_deducted: int
    new_balance: int


class InsufficientDepositError(BaseModel):
    """Error response for insufficient deposit"""
    error: Literal["insufficient_deposit"] = "insufficient_deposit"
    warnings: int
    required_amount: int
    current_balance: int
    shortfall: int


# ============================================================
# Bid Schemas
# ============================================================

class BidCreateRequest(BaseModel):
    """Request schema for creating a bid on an order"""
    price_cents: int = Field(..., gt=0, description="Bid amount in cents")


class BidResponse(BaseModel):
    """Bid response schema"""
    id: int
    deliveryPersonID: int
    orderID: int
    bidAmount: int
    delivery_person_email: Optional[str] = None

    class Config:
        from_attributes = True


class BidListResponse(BaseModel):
    """List of bids for an order"""
    order_id: int
    bids: List[BidResponse]


class AssignDeliveryRequest(BaseModel):
    """Request for manager to assign delivery"""
    delivery_id: int = Field(..., description="Delivery person account ID")
    memo: Optional[str] = Field(None, max_length=500, description="Assignment memo/note")


class AssignDeliveryResponse(BaseModel):
    """Response after assigning delivery"""
    message: str
    order_id: int
    assigned_delivery_id: int
    bid_id: int
    delivery_fee: int
    order_status: str


# ============================================================
# Thread/Post Schemas
# ============================================================

class ThreadCreateRequest(BaseModel):
    """Request for creating a thread"""
    topic: str = Field(..., min_length=1, max_length=255)
    restaurantID: int


class ThreadResponse(BaseModel):
    """Thread response schema"""
    id: int
    topic: str
    restaurantID: int

    class Config:
        from_attributes = True


class PostCreateRequest(BaseModel):
    """Request for creating a post"""
    threadID: int
    title: Optional[str] = Field(None, max_length=255)
    body: str = Field(..., min_length=1)


class PostResponse(BaseModel):
    """Post response schema"""
    id: int
    threadID: int
    posterID: int
    title: Optional[str]
    body: str
    datetime: Optional[str]

    class Config:
        from_attributes = True


# ============================================================
# Agent Query/Answer Schemas
# ============================================================

class AgentQueryRequest(BaseModel):
    """Request for an AI query"""
    question: str = Field(..., min_length=1)
    restaurantID: Optional[int] = None


class AgentQueryResponse(BaseModel):
    """Agent query response"""
    id: int
    question: str
    restaurantID: Optional[int]

    class Config:
        from_attributes = True


class AgentAnswerResponse(BaseModel):
    """Agent answer response"""
    ID: int
    queryID: int
    answer: str
    average_rating: float
    reviews: int

    class Config:
        from_attributes = True


# ============================================================
# Complaint Schemas
# ============================================================

class ComplaintCreateRequest(BaseModel):
    """Request for filing a complaint"""
    accountID: int = Field(..., description="Account being complained about")
    type: str = Field(..., description="Type of complaint")
    description: str = Field(..., min_length=1)


class ComplaintResponse(BaseModel):
    """Complaint response schema"""
    id: int
    accountID: int
    type: str
    description: str
    filer: int

    class Config:
        from_attributes = True


# ============================================================
# Delivery Rating Schemas
# ============================================================

class DeliveryRatingResponse(BaseModel):
    """Delivery rating response"""
    accountID: int
    averageRating: float
    reviews: int

    class Config:
        from_attributes = True


# ============================================================
# Closure Request Schemas
# ============================================================

class ClosureRequestCreate(BaseModel):
    """Request for account closure"""
    reason: Optional[str] = None


class ClosureRequestResponse(BaseModel):
    """Closure request response"""
    accountID: int
    reason: Optional[str]

    class Config:
        from_attributes = True


# ============================================================
# Open Request Schemas
# ============================================================

class OpenRequestCreate(BaseModel):
    """Request to open/join a restaurant"""
    restaurantID: int
    email: EmailStr
    password: str = Field(..., min_length=8)


class OpenRequestResponse(BaseModel):
    """Open request response"""
    id: int
    restaurantID: int
    email: str

    class Config:
        from_attributes = True


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


# ============================================================
# Transaction Schemas (Audit Log)
# ============================================================

class TransactionResponse(BaseModel):
    """Transaction audit log entry"""
    id: int
    accountID: int
    amount_cents: int
    balance_before: int
    balance_after: int
    transaction_type: str
    reference_type: Optional[str]
    reference_id: Optional[int]
    description: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """List of transactions"""
    transactions: List[TransactionResponse]
    total: int
