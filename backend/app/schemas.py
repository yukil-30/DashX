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


class ManagerRegisterRequest(BaseModel):
    """Manager registration request - also creates a new restaurant"""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 chars)")
    restaurant_name: str = Field(..., min_length=1, max_length=255, description="Name of the new restaurant")
    
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
    free_delivery_credits: int = 0

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
    order_id: Optional[int] = Field(None, description="Order ID to bid on (for POST /bids)")
    price_cents: int = Field(..., gt=0, description="Bid amount in cents")
    estimated_minutes: int = Field(30, gt=0, le=180, description="Estimated delivery time in minutes")


class BidResponse(BaseModel):
    """Bid response schema"""
    id: int
    deliveryPersonID: int
    orderID: int
    bidAmount: int
    estimated_minutes: int = 30
    delivery_person_email: Optional[str] = None
    is_lowest: bool = False

    class Config:
        from_attributes = True


class DeliveryPersonStats(BaseModel):
    """Delivery person statistics for manager view"""
    account_id: int
    email: str
    average_rating: float = 0.0
    reviews: int = 0
    total_deliveries: int = 0
    on_time_deliveries: int = 0
    on_time_percentage: float = 0.0
    avg_delivery_minutes: int = 30
    warnings: int = 0


class BidWithStats(BaseModel):
    """Bid with delivery person stats for manager view"""
    id: int
    deliveryPersonID: int
    orderID: int
    bidAmount: int
    estimated_minutes: int = 30
    is_lowest: bool = False
    delivery_person: DeliveryPersonStats


class BidListResponse(BaseModel):
    """List of bids for an order"""
    order_id: int
    bids: List[BidResponse]
    lowest_bid_id: Optional[int] = None


class BidListWithStatsResponse(BaseModel):
    """List of bids with delivery person stats for manager"""
    order_id: int
    bids: List[BidWithStats]
    lowest_bid_id: Optional[int] = None


class AssignDeliveryRequest(BaseModel):
    """Request for manager to assign delivery"""
    delivery_id: int = Field(..., description="Delivery person account ID")
    memo: Optional[str] = Field(None, max_length=500, description="Assignment memo/note (required if not lowest bid)")


class AssignDeliveryResponse(BaseModel):
    """Response after assigning delivery"""
    message: str
    order_id: int
    assigned_delivery_id: int
    bid_id: int
    delivery_fee: int
    order_status: str
    is_lowest_bid: bool = True
    memo_saved: bool = False


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
    """Request for filing a complaint or compliment"""
    from_user_id: Optional[int] = Field(None, description="User filing the complaint (auto-set from token)")
    about_user_id: Optional[int] = Field(None, description="User being complained about (null for general)")
    order_id: Optional[int] = Field(None, description="Related order (optional but recommended for validation)")
    type: Literal["complaint", "compliment"] = Field(..., description="Type of feedback")
    text: str = Field(..., min_length=1, max_length=2000, description="Complaint/compliment description")
    target_type: Optional[Literal["chef", "delivery", "customer"]] = Field(
        None, description="Role of person being complained about (for validation)"
    )


class DisputeRequest(BaseModel):
    """Request to dispute a complaint"""
    reason: str = Field(..., min_length=10, max_length=2000, description="Reason for disputing the complaint")


class ComplaintResponse(BaseModel):
    """Complaint response schema"""
    id: int
    accountID: Optional[int]
    type: str
    description: str
    filer: int
    filer_email: Optional[str] = None
    about_email: Optional[str] = None
    order_id: Optional[int] = None
    status: str = "pending"
    resolution: Optional[str] = None
    resolved_by: Optional[int] = None
    resolved_at: Optional[str] = None
    created_at: Optional[str] = None
    # Dispute fields
    disputed: bool = False
    dispute_reason: Optional[str] = None
    disputed_at: Optional[str] = None
    target_type: Optional[str] = None

    class Config:
        from_attributes = True


class ComplaintListResponse(BaseModel):
    """List of complaints"""
    complaints: List[ComplaintResponse]
    total: int
    unresolved_count: int


class ComplaintResolveRequest(BaseModel):
    """Request to resolve a complaint"""
    resolution: Literal["dismissed", "warning_issued"] = Field(
        ..., 
        description="dismissed = without merit (complainant gets warning), warning_issued = valid complaint"
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Resolution notes")


class ComplaintResolveResponse(BaseModel):
    """Response after resolving a complaint"""
    message: str
    complaint_id: int
    resolution: str
    warning_applied_to: Optional[int] = None
    warning_count: Optional[int] = None
    account_status_changed: Optional[str] = None
    audit_log_id: int


class DisputeResponse(BaseModel):
    """Response after disputing a complaint"""
    message: str
    complaint_id: int
    disputed: bool = True
    dispute_reason: str
    status: str = "disputed"
    disputed_at: str


class DisputedComplaintListResponse(BaseModel):
    """List of disputed complaints for manager queue"""
    complaints: List[ComplaintResponse]
    total: int
    pending_count: int


# ============================================================
# Audit Log Schemas
# ============================================================

class AuditLogResponse(BaseModel):
    """Audit log entry response"""
    id: int
    action_type: str
    actor_id: Optional[int]
    target_id: Optional[int]
    complaint_id: Optional[int]
    order_id: Optional[int]
    details: Optional[dict] = None
    created_at: str

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """List of audit log entries"""
    entries: List[AuditLogResponse]
    total: int


# ============================================================
# Manager Notification Schemas
# ============================================================

class ManagerNotificationResponse(BaseModel):
    """Manager notification response"""
    id: int
    notification_type: str
    title: str
    message: str
    related_account_id: Optional[int]
    related_order_id: Optional[int]
    is_read: bool
    created_at: str

    class Config:
        from_attributes = True


class ManagerNotificationListResponse(BaseModel):
    """List of manager notifications"""
    notifications: List[ManagerNotificationResponse]
    total: int
    unread_count: int


# ============================================================
# Login Response with Warnings
# ============================================================

class LoginWarningInfo(BaseModel):
    """Warning information returned on login"""
    warnings_count: int
    warning_message: Optional[str] = None
    is_near_threshold: bool = False


class TokenResponseWithWarnings(BaseModel):
    """JWT token response with warning info"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiry in seconds")
    warning_info: Optional[LoginWarningInfo] = None


# ============================================================
# Delivery Rating Schemas
# ============================================================

class DeliveryRatingResponse(BaseModel):
    """Delivery rating response"""
    accountID: int
    averageRating: float
    reviews: int
    total_deliveries: int = 0
    on_time_deliveries: int = 0
    on_time_percentage: float = 0.0
    avg_delivery_minutes: int = 30

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


# ============================================================
# Chat/Knowledge Base Schemas
# ============================================================

class ChatQueryRequest(BaseModel):
    """Request for chat query"""
    user_id: Optional[int] = Field(None, description="User ID (optional, taken from token if authenticated)")
    question: str = Field(..., min_length=1, max_length=2000, description="The question to ask")


class ChatQueryResponse(BaseModel):
    """Response from chat query"""
    chat_id: int = Field(..., description="Chat log ID for rating")
    question: str
    answer: str
    source: str = Field(..., description="'kb' for knowledge base, 'llm' for LLM-generated")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score of the answer")
    kb_entry_id: Optional[int] = Field(None, description="Knowledge base entry ID if source='kb'")


class ChatRateRequest(BaseModel):
    """Request to rate a chat response"""
    rating: int = Field(..., ge=0, le=5, description="Rating 0-5. 0 = flag for review, 1-5 = satisfaction")


class ChatRateResponse(BaseModel):
    """Response after rating"""
    message: str
    chat_id: int
    rating: int
    flagged: bool = Field(default=False, description="True if rating=0 and flagged for manager review")


class KnowledgeBaseEntry(BaseModel):
    """Knowledge base entry response"""
    id: int
    question: str
    answer: str
    keywords: Optional[str] = None
    confidence: float
    author_id: Optional[int] = None
    is_active: bool = True
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class KnowledgeBaseCreateRequest(BaseModel):
    """Request to create a KB entry"""
    question: str = Field(..., min_length=1, max_length=1000)
    answer: str = Field(..., min_length=1, max_length=5000)
    keywords: Optional[str] = Field(None, max_length=500, description="Comma-separated keywords")
    confidence: float = Field(default=0.8, ge=0, le=1)


class KnowledgeBaseUpdateRequest(BaseModel):
    """Request to update a KB entry"""
    question: Optional[str] = Field(None, min_length=1, max_length=1000)
    answer: Optional[str] = Field(None, min_length=1, max_length=5000)
    keywords: Optional[str] = Field(None, max_length=500)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None


class FlaggedChatResponse(BaseModel):
    """Flagged chat entry for manager review"""
    id: int
    user_id: int
    user_email: Optional[str] = None
    question: str
    answer: str
    source: str
    confidence: Optional[float] = None
    rating: int
    kb_entry_id: Optional[int] = None
    created_at: Optional[str] = None
    reviewed: bool = False

    class Config:
        from_attributes = True


class FlaggedChatListResponse(BaseModel):
    """List of flagged chats for manager"""
    flagged_chats: List[FlaggedChatResponse]
    total: int


class ReviewFlaggedRequest(BaseModel):
    """Request to review a flagged chat"""
    action: Literal["dismiss", "remove_kb", "disable_author"] = Field(
        ...,
        description="dismiss = mark as reviewed, remove_kb = remove KB entry, disable_author = deactivate author's KB entries"
    )
    notes: Optional[str] = Field(None, max_length=1000)


class ReviewFlaggedResponse(BaseModel):
    """Response after reviewing flagged chat"""
    message: str
    chat_id: int
    action_taken: str
    kb_entries_affected: int = 0


# ============================================================
# Voice Report Schemas
# ============================================================

class VoiceReportSubmitResponse(BaseModel):
    """Response after submitting a voice report"""
    message: str
    report_id: int
    status: str = "pending"
    audio_file_path: str
    file_size_bytes: int


class VoiceReportResponse(BaseModel):
    """Voice report response for manager dashboard"""
    id: int
    submitter_id: int
    submitter_email: Optional[str] = None
    submitter_type: Optional[str] = None
    audio_file_path: str
    audio_url: Optional[str] = None  # URL to stream/download audio
    file_size_bytes: int
    duration_seconds: Optional[int] = None
    mime_type: str
    transcription: Optional[str] = None
    sentiment: Optional[str] = None
    subjects: Optional[List[str]] = None
    auto_labels: Optional[List[str]] = None
    confidence_score: Optional[float] = None
    status: str
    is_processed: bool
    related_order_id: Optional[int] = None
    related_account_id: Optional[int] = None
    related_account_email: Optional[str] = None
    processing_error: Optional[str] = None
    manager_notes: Optional[str] = None
    resolved_by: Optional[int] = None
    resolved_at: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class VoiceReportListResponse(BaseModel):
    """List of voice reports for manager dashboard"""
    reports: List[VoiceReportResponse]
    total: int
    pending_count: int
    unresolved_complaints: int


class VoiceReportResolveRequest(BaseModel):
    """Request to resolve a voice report"""
    action: Literal["dismiss", "warning", "refer_to_complaint"] = Field(
        ...,
        description="dismiss = no action, warning = issue warning to subject, refer_to_complaint = create formal complaint"
    )
    notes: Optional[str] = Field(None, max_length=2000, description="Manager notes")
    related_account_id: Optional[int] = Field(None, description="Account ID of person report is about (required for warning)")


class VoiceReportResolveResponse(BaseModel):
    """Response after resolving a voice report"""
    message: str
    report_id: int
    action_taken: str
    warning_applied: bool = False
    complaint_created_id: Optional[int] = None
    resolved_at: str


# ============================================================
# Customer Dashboard Schemas
# ============================================================

class VIPStatus(BaseModel):
    """VIP status information"""
    is_vip: bool = False
    total_spent_cents: int = 0
    total_spent_formatted: str = "$0.00"
    completed_orders: int = 0
    has_unresolved_complaints: bool = False
    vip_eligible: bool = False
    vip_reason: Optional[str] = None  # Why they are/aren't VIP
    free_delivery_credits: int = 0
    discount_percent: int = 0  # 5% for VIP, 0 otherwise
    next_free_delivery_in: int = 0  # Orders until next free delivery


class CustomerDashboardResponse(BaseModel):
    """Customer dashboard data"""
    user_id: int
    email: str
    account_type: str
    balance_cents: int
    balance_formatted: str
    vip_status: VIPStatus
    recent_orders: List["OrderSummary"] = []
    favorite_dishes: List[DishResponse] = []
    most_popular_dish: Optional[DishResponse] = None
    highest_rated_dish: Optional[DishResponse] = None
    top_rated_chef: Optional["ChefProfileSummary"] = None


class OrderSummary(BaseModel):
    """Brief order summary for lists"""
    id: int
    status: str
    total_cents: int
    total_formatted: str
    items_count: int
    created_at: str
    can_review: bool = False  # Can leave reviews?

    class Config:
        from_attributes = True


class ChefProfileSummary(BaseModel):
    """Chef summary for dashboard"""
    id: int
    email: str
    display_name: Optional[str] = None
    profile_picture: Optional[str] = None
    specialty: Optional[str] = None
    average_rating: float = 0.0
    total_dishes: int = 0
    total_reviews: int = 0

    class Config:
        from_attributes = True


# ============================================================
# Profile Schemas
# ============================================================

class ProfileUpdateRequest(BaseModel):
    """Request to update profile"""
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=2000)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    specialty: Optional[str] = Field(None, max_length=255)


class ProfileResponse(BaseModel):
    """Full profile response"""
    account_id: int
    email: str
    account_type: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    profile_picture: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    specialty: Optional[str] = None
    created_at: Optional[str] = None
    # Stats
    total_orders: int = 0
    total_reviews_given: int = 0
    average_rating_given: float = 0.0
    # For chefs
    dishes_created: int = 0
    average_dish_rating: float = 0.0
    # For delivery
    total_deliveries: int = 0
    average_delivery_rating: float = 0.0
    on_time_percentage: float = 0.0

    class Config:
        from_attributes = True


class ChefProfileResponse(ProfileResponse):
    """Extended chef profile with dishes"""
    dishes: List[DishResponse] = []


class DeliveryProfileResponse(ProfileResponse):
    """Extended delivery person profile"""
    total_deliveries: int = 0
    on_time_deliveries: int = 0


# ============================================================
# Review Schemas
# ============================================================

class DishReviewCreateRequest(BaseModel):
    """Request to create a dish review"""
    dish_id: int = Field(..., description="Dish ID to review")
    order_id: int = Field(..., description="Order ID that included this dish")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    review_text: Optional[str] = Field(None, max_length=2000)


class DishReviewResponse(BaseModel):
    """Dish review response"""
    id: int
    dish_id: int
    dish_name: str
    account_id: int
    reviewer_email: Optional[str] = None
    order_id: Optional[int]
    rating: int
    review_text: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class DishReviewListResponse(BaseModel):
    """List of dish reviews"""
    reviews: List[DishReviewResponse]
    total: int
    average_rating: float


class DeliveryReviewCreateRequest(BaseModel):
    """Request to create a delivery review"""
    order_id: int = Field(..., description="Order ID to review delivery for")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    review_text: Optional[str] = Field(None, max_length=2000)
    on_time: Optional[bool] = Field(None, description="Was delivery on time?")


class DeliveryReviewResponse(BaseModel):
    """Delivery review response"""
    id: int
    order_id: int
    delivery_person_id: int
    delivery_person_email: Optional[str] = None
    reviewer_id: int
    rating: int
    review_text: Optional[str]
    on_time: Optional[bool]
    created_at: str

    class Config:
        from_attributes = True


# ============================================================
# Forum Schemas (Enhanced)
# ============================================================

class ThreadCreateRequest(BaseModel):
    """Request for creating a thread"""
    topic: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1, max_length=5000, description="Initial post body")
    category: Optional[str] = Field(None, description="Thread category: chef, dish, delivery, general")


class ThreadDetailResponse(BaseModel):
    """Detailed thread response with posts"""
    id: int
    topic: str
    restaurantID: int
    created_by_id: int
    created_by_email: Optional[str] = None
    category: Optional[str] = None
    posts_count: int = 0
    created_at: Optional[str] = None
    posts: List["PostResponse"] = []

    class Config:
        from_attributes = True


class ThreadListResponse(BaseModel):
    """List of forum threads"""
    threads: List[ThreadDetailResponse]
    total: int
    page: int
    per_page: int


class PostCreateRequest(BaseModel):
    """Request for creating a post in a thread"""
    body: str = Field(..., min_length=1, max_length=5000)
    title: Optional[str] = Field(None, max_length=255)


# ============================================================
# Order History Schemas
# ============================================================

class OrderHistoryItem(BaseModel):
    """Order item for history view"""
    dish_id: int
    dish_name: str
    dish_picture: Optional[str] = None
    quantity: int
    unit_price_cents: int
    can_review: bool = False
    has_reviewed: bool = False

    class Config:
        from_attributes = True


class OrderHistoryResponse(BaseModel):
    """Detailed order for history view"""
    id: int
    status: str
    created_at: str
    delivered_at: Optional[str] = None
    subtotal_cents: int
    delivery_fee_cents: int
    discount_cents: int
    total_cents: int
    total_formatted: str
    delivery_address: str
    note: Optional[str] = None
    items: List[OrderHistoryItem] = []
    # Delivery info
    delivery_person_id: Optional[int] = None
    delivery_person_email: Optional[str] = None
    can_review_delivery: bool = False
    has_reviewed_delivery: bool = False
    # VIP info
    free_delivery_used: bool = False
    vip_discount_applied: bool = False

    class Config:
        from_attributes = True


class OrderHistoryListResponse(BaseModel):
    """Paginated order history"""
    orders: List[OrderHistoryResponse]
    total: int
    page: int
    per_page: int


# ============================================================
# VIP Schemas
# ============================================================

class VIPHistoryEntry(BaseModel):
    """VIP status change entry"""
    id: int
    previous_type: str
    new_type: str
    reason: Optional[str]
    changed_by: Optional[int]
    created_at: str

    class Config:
        from_attributes = True


class VIPHistoryResponse(BaseModel):
    """VIP history for an account"""
    entries: List[VIPHistoryEntry]
    total: int


# Rebuild models with forward references
CustomerDashboardResponse.model_rebuild()

