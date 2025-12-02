"""
SQLAlchemy ORM Models for DashX
Matches exactly the authoritative database schema.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Numeric, ForeignKey, Boolean
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Restaurant(Base):
    """Restaurant entity"""
    __tablename__ = "restaurant"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)

    # Relationships
    accounts = relationship("Account", back_populates="restaurant")
    dishes = relationship("Dish", back_populates="restaurant")
    threads = relationship("Thread", back_populates="restaurant")
    agent_queries = relationship("AgentQuery", back_populates="restaurant")
    open_requests = relationship("OpenRequest", back_populates="restaurant")


class Account(Base):
    """User accounts - visitors, customers, VIPs, employees"""
    __tablename__ = "accounts"

    ID = Column(Integer, primary_key=True)
    restaurantID = Column(Integer, ForeignKey("restaurant.id", ondelete="SET NULL"), nullable=True)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    warnings = Column(Integer, nullable=False, default=0)
    type = Column(String(50), nullable=False, default='visitor')
    balance = Column(Integer, nullable=False, default=0)  # In cents
    wage = Column(Integer, nullable=True)  # Hourly wage in cents for employees
    free_delivery_credits = Column(Integer, nullable=False, default=0)  # Free delivery credits for VIP
    completed_orders_count = Column(Integer, nullable=False, default=0)  # Track orders for VIP free delivery
    
    # Chef/employee tracking
    times_demoted = Column(Integer, nullable=False, default=0)
    is_fired = Column(Boolean, nullable=False, default=False)
    is_blacklisted = Column(Boolean, nullable=False, default=False)
    previous_type = Column(String(50), nullable=True)  # For VIP->customer demotion tracking

    # Relationships
    restaurant = relationship("Restaurant", back_populates="accounts")
    orders = relationship("Order", back_populates="account")
    dishes_created = relationship("Dish", back_populates="chef", foreign_keys="Dish.chefID")
    bids = relationship("Bid", back_populates="delivery_person")
    posts = relationship("Post", back_populates="poster")
    complaints_about = relationship("Complaint", back_populates="account", foreign_keys="Complaint.accountID")
    complaints_filed = relationship("Complaint", back_populates="filer_account", foreign_keys="Complaint.filer")
    delivery_rating = relationship("DeliveryRating", back_populates="account", uselist=False)
    closure_request = relationship("ClosureRequest", back_populates="account", uselist=False)
    transactions = relationship("Transaction", back_populates="account")


class Dish(Base):
    """Menu items available at the restaurant"""
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True)
    restaurantID = Column(Integer, ForeignKey("restaurant.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cost = Column(Integer, nullable=False)  # In cents
    picture = Column(Text, nullable=True)  # URL/path to image
    average_rating = Column(Numeric(3, 2), nullable=True, default=0.00)
    reviews = Column(Integer, nullable=False, default=0)
    chefID = Column(Integer, ForeignKey("accounts.ID", ondelete="SET NULL"), nullable=True)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="dishes")
    chef = relationship("Account", back_populates="dishes_created", foreign_keys=[chefID])
    ordered_dishes = relationship("OrderedDish", back_populates="dish")


class Order(Base):
    """Customer orders"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    accountID = Column(Integer, ForeignKey("accounts.ID", ondelete="RESTRICT"), nullable=False)
    dateTime = Column(Text, nullable=True)  # Stored as text per schema
    finalCost = Column(Integer, nullable=False)  # Total in cents (items + delivery)
    status = Column(String(50), nullable=False, default='pending')
    bidID = Column(Integer, ForeignKey("bid.id", ondelete="SET NULL"), nullable=True)
    note = Column(Text, nullable=True)
    delivery_address = Column(Text, nullable=True)  # Delivery address for the order
    delivery_fee = Column(Integer, nullable=False, default=0)  # Delivery fee in cents
    subtotal_cents = Column(Integer, nullable=False, default=0)  # Items total before discount/delivery
    discount_cents = Column(Integer, nullable=False, default=0)  # VIP discount applied
    free_delivery_used = Column(Integer, nullable=False, default=0)  # 1 if free delivery used
    assignment_memo = Column(Text, nullable=True)  # Manager memo when non-lowest bid assigned

    # Relationships
    account = relationship("Account", back_populates="orders")
    accepted_bid = relationship("Bid", back_populates="order_accepted", foreign_keys=[bidID])
    ordered_dishes = relationship("OrderedDish", back_populates="order", cascade="all, delete-orphan")
    bids = relationship("Bid", back_populates="order", foreign_keys="Bid.orderID")


class OrderedDish(Base):
    """Junction table for orders and dishes - composite primary key"""
    __tablename__ = "ordered_dishes"

    DishID = Column(Integer, ForeignKey("dishes.id", ondelete="RESTRICT"), primary_key=True)
    orderID = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True)
    quantity = Column(Integer, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="ordered_dishes")
    dish = relationship("Dish", back_populates="ordered_dishes")


class Bid(Base):
    """Delivery person bids on orders"""
    __tablename__ = "bid"

    id = Column(Integer, primary_key=True)
    deliveryPersonID = Column(Integer, ForeignKey("accounts.ID", ondelete="CASCADE"), nullable=False)
    orderID = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    bidAmount = Column(Integer, nullable=False)  # In cents
    estimated_minutes = Column(Integer, nullable=False, default=30)  # Estimated delivery time

    # Relationships
    delivery_person = relationship("Account", back_populates="bids")
    order = relationship("Order", back_populates="bids", foreign_keys=[orderID])
    order_accepted = relationship("Order", back_populates="accepted_bid", foreign_keys="Order.bidID")


class Thread(Base):
    """Forum discussion threads"""
    __tablename__ = "thread"

    id = Column(Integer, primary_key=True)
    topic = Column(String(255), nullable=False)
    restaurantID = Column(Integer, ForeignKey("restaurant.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="threads")
    posts = relationship("Post", back_populates="thread", cascade="all, delete-orphan")


class Post(Base):
    """Forum posts within threads"""
    __tablename__ = "post"

    id = Column(Integer, primary_key=True)
    threadID = Column(Integer, ForeignKey("thread.id", ondelete="CASCADE"), nullable=False)
    posterID = Column(Integer, ForeignKey("accounts.ID", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    datetime = Column(Text, nullable=True)  # Stored as text per schema

    # Relationships
    thread = relationship("Thread", back_populates="posts")
    poster = relationship("Account", back_populates="posts")


class AgentQuery(Base):
    """AI/LLM queries from users"""
    __tablename__ = "agent_query"

    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    restaurantID = Column(Integer, ForeignKey("restaurant.id", ondelete="CASCADE"), nullable=True)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="agent_queries")
    answers = relationship("AgentAnswer", back_populates="query", cascade="all, delete-orphan")


class AgentAnswer(Base):
    """AI/LLM responses to queries"""
    __tablename__ = "agent_answer"

    ID = Column(Integer, primary_key=True)
    queryID = Column(Integer, ForeignKey("agent_query.id", ondelete="CASCADE"), nullable=False)
    answer = Column(Text, nullable=False)
    average_rating = Column(Numeric(3, 2), nullable=True, default=0.00)
    reviews = Column(Integer, nullable=False, default=0)

    # Relationships
    query = relationship("AgentQuery", back_populates="answers")


class DeliveryRating(Base):
    """Ratings for delivery personnel - accountID is PK"""
    __tablename__ = "DeliveryRating"

    accountID = Column(Integer, ForeignKey("accounts.ID", ondelete="CASCADE"), primary_key=True)
    averageRating = Column(Numeric(3, 2), nullable=True, default=0.00)
    reviews = Column(Integer, nullable=False, default=0)
    total_deliveries = Column(Integer, nullable=False, default=0)
    on_time_deliveries = Column(Integer, nullable=False, default=0)
    avg_delivery_minutes = Column(Integer, nullable=False, default=30)

    # Relationships
    account = relationship("Account", back_populates="delivery_rating")


class Complaint(Base):
    """Complaints/compliments table"""
    __tablename__ = "complaint"

    id = Column(Integer, primary_key=True)
    accountID = Column(Integer, ForeignKey("accounts.ID", ondelete="CASCADE"), nullable=True)  # Nullable for general complaints
    type = Column(String(50), nullable=False)  # 'complaint' or 'compliment'
    description = Column(Text, nullable=False)
    filer = Column(Integer, ForeignKey("accounts.ID", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), nullable=False, default='pending')  # pending, resolved
    resolution = Column(String(50), nullable=True)  # dismissed, warning_issued
    resolved_by = Column(Integer, ForeignKey("accounts.ID", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(Text, nullable=True)  # ISO timestamp
    created_at = Column(Text, nullable=True)  # ISO timestamp

    # Relationships
    account = relationship("Account", back_populates="complaints_about", foreign_keys=[accountID])
    filer_account = relationship("Account", back_populates="complaints_filed", foreign_keys=[filer])
    order = relationship("Order", backref="complaints")
    resolver = relationship("Account", foreign_keys=[resolved_by])


class ClosureRequest(Base):
    """Account closure/deletion requests - accountID is PK"""
    __tablename__ = "closureRequest"

    accountID = Column(Integer, ForeignKey("accounts.ID", ondelete="CASCADE"), primary_key=True)
    reason = Column(Text, nullable=True)

    # Relationships
    account = relationship("Account", back_populates="closure_request")


class OpenRequest(Base):
    """Applications to open/join a restaurant"""
    __tablename__ = "openRequest"

    id = Column(Integer, primary_key=True)  # Adding ID for proper querying
    restaurantID = Column(Integer, ForeignKey("restaurant.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="open_requests")


class Transaction(Base):
    """Audit log for all balance changes"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    accountID = Column(Integer, ForeignKey("accounts.ID", ondelete="CASCADE"), nullable=False)
    amount_cents = Column(Integer, nullable=False)  # Positive for credit, negative for debit
    balance_before = Column(Integer, nullable=False)  # Balance before this transaction
    balance_after = Column(Integer, nullable=False)  # Balance after this transaction
    transaction_type = Column(String(50), nullable=False)  # 'deposit', 'order_payment', 'refund', etc.
    reference_type = Column(String(50), nullable=True)  # 'order', 'deposit', etc.
    reference_id = Column(Integer, nullable=True)  # ID of the related order, etc.
    description = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)  # ISO timestamp

    # Relationships
    account = relationship("Account", back_populates="transactions")


class AuditLog(Base):
    """Immutable audit log for reputation-related actions"""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    action_type = Column(String(100), nullable=False)  # complaint_filed, complaint_resolved, warning_issued, etc.
    actor_id = Column(Integer, ForeignKey("accounts.ID", ondelete="SET NULL"), nullable=True)
    target_id = Column(Integer, ForeignKey("accounts.ID", ondelete="SET NULL"), nullable=True)
    complaint_id = Column(Integer, ForeignKey("complaint.id", ondelete="SET NULL"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    details = Column(JSONB, nullable=True)  # Additional context
    created_at = Column(Text, nullable=False)  # ISO timestamp

    # Relationships
    actor = relationship("Account", foreign_keys=[actor_id])
    target = relationship("Account", foreign_keys=[target_id])
    complaint = relationship("Complaint")
    order = relationship("Order")


class Blacklist(Base):
    """Permanently banned users"""
    __tablename__ = "blacklist"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    reason = Column(Text, nullable=True)
    original_account_id = Column(Integer, nullable=True)
    blacklisted_by = Column(Integer, ForeignKey("accounts.ID", ondelete="SET NULL"), nullable=True)
    created_at = Column(Text, nullable=False)  # ISO timestamp

    # Relationships
    blacklisted_by_account = relationship("Account", foreign_keys=[blacklisted_by])


class ManagerNotification(Base):
    """System alerts for managers"""
    __tablename__ = "manager_notifications"

    id = Column(Integer, primary_key=True)
    notification_type = Column(String(100), nullable=False)  # chef_performance, delivery_issue, etc.
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    related_account_id = Column(Integer, ForeignKey("accounts.ID", ondelete="SET NULL"), nullable=True)
    related_order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(Text, nullable=False)  # ISO timestamp

    # Relationships
    related_account = relationship("Account", foreign_keys=[related_account_id])
    related_order = relationship("Order")


class KnowledgeBase(Base):
    """Knowledge base entries for FAQ/chat support"""
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    keywords = Column(Text, nullable=True)  # Comma-separated keywords
    confidence = Column(Numeric(3, 2), nullable=False, default=0.80)
    author_id = Column(Integer, ForeignKey("accounts.ID", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(Text, nullable=True)
    updated_at = Column(Text, nullable=True)

    # Relationships
    author = relationship("Account", foreign_keys=[author_id])
    chat_logs = relationship("ChatLog", back_populates="kb_entry")


class ChatLog(Base):
    """Chat interaction log for audit and rating"""
    __tablename__ = "chat_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("accounts.ID", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    source = Column(String(10), nullable=False)  # 'kb' or 'llm'
    kb_entry_id = Column(Integer, ForeignKey("knowledge_base.id", ondelete="SET NULL"), nullable=True)
    confidence = Column(Numeric(3, 2), nullable=True)
    rating = Column(Integer, nullable=True)  # 0-5, where 0 = flagged
    flagged = Column(Boolean, nullable=False, default=False)
    reviewed = Column(Boolean, nullable=False, default=False)
    reviewed_by = Column(Integer, ForeignKey("accounts.ID", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(Text, nullable=True)
    created_at = Column(Text, nullable=True)

    # Relationships
    user = relationship("Account", foreign_keys=[user_id])
    kb_entry = relationship("KnowledgeBase", back_populates="chat_logs")
    reviewer = relationship("Account", foreign_keys=[reviewed_by])


class VoiceReport(Base):
    """Voice-based complaint/compliment reports with transcription and NLP analysis"""
    __tablename__ = "voice_reports"

    id = Column(Integer, primary_key=True)
    submitter_id = Column(Integer, ForeignKey("accounts.ID", ondelete="CASCADE"), nullable=False)
    audio_file_path = Column(Text, nullable=False)  # Path to stored audio file
    file_size_bytes = Column(Integer, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=False, default='audio/mpeg')
    transcription = Column(Text, nullable=True)  # Transcribed text
    sentiment = Column(String(50), nullable=True)  # complaint, compliment, neutral
    subjects = Column(JSONB, nullable=True)  # Extracted subjects: ["chef", "driver", "staff"]
    auto_labels = Column(JSONB, nullable=True)  # Auto-generated labels: ["Complaint Chef", "Food Quality"]
    confidence_score = Column(Numeric(3, 2), nullable=True)  # NLP confidence 0.00-1.00
    status = Column(String(50), nullable=False, default='pending')  # pending, transcribed, analyzed, resolved
    is_processed = Column(Boolean, nullable=False, default=False)  # Has transcription & NLP completed
    related_order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    related_account_id = Column(Integer, ForeignKey("accounts.ID", ondelete="SET NULL"), nullable=True)
    processing_error = Column(Text, nullable=True)  # Error message if processing fails
    manager_notes = Column(Text, nullable=True)
    resolved_by = Column(Integer, ForeignKey("accounts.ID", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(Text, nullable=True)  # ISO timestamp
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    # Relationships
    submitter = relationship("Account", foreign_keys=[submitter_id], backref="voice_reports_submitted")
    related_account = relationship("Account", foreign_keys=[related_account_id])
    related_order = relationship("Order", foreign_keys=[related_order_id])
    resolver = relationship("Account", foreign_keys=[resolved_by])
