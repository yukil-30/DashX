"""
SQLAlchemy ORM Models for DashX
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime, 
    Numeric, ForeignKey, Enum as SQLEnum, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from app.database import Base
import enum


class AccountType(str, enum.Enum):
    """Account type enum matching database ENUM"""
    VISITOR = "visitor"
    CUSTOMER = "customer"
    VIP = "vip"
    CHEF = "chef"
    DELIVERY = "delivery"
    MANAGER = "manager"


class OrderStatus(str, enum.Enum):
    """Order status enum matching database ENUM"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class TransactionType(str, enum.Enum):
    """Transaction type enum matching database ENUM"""
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    ORDER_PAYMENT = "order_payment"
    ORDER_REFUND = "order_refund"
    WAGE_PAYMENT = "wage_payment"
    TIP = "tip"
    DELIVERY_FEE = "delivery_fee"


# Use PostgreSQL ENUM type
account_type_enum = ENUM(
    'visitor', 'customer', 'vip', 'chef', 'delivery', 'manager',
    name='account_type',
    create_type=False  # Type already exists in database
)

order_status_enum = ENUM(
    'pending', 'confirmed', 'preparing', 'ready', 'out_for_delivery',
    'delivered', 'cancelled', 'refunded',
    name='order_status',
    create_type=False
)

transaction_type_enum = ENUM(
    'deposit', 'withdrawal', 'order_payment', 'order_refund',
    'wage_payment', 'tip', 'delivery_fee',
    name='transaction_type',
    create_type=False
)


class Restaurant(Base):
    """Restaurant entity - central to the system"""
    __tablename__ = "restaurant"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    phone = Column(String(20))
    email = Column(String(255))
    description = Column(Text)
    opening_hours = Column(JSONB)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    accounts = relationship("Account", back_populates="restaurant")
    orders = relationship("Order", back_populates="restaurant")
    dishes = relationship("Dish", back_populates="restaurant")


class Account(Base):
    """User accounts - visitors, customers, VIPs, employees"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey("restaurant.id", ondelete="SET NULL"))
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    address = Column(Text)
    account_type = Column(account_type_enum, nullable=False, default='visitor')
    balance = Column(Integer, nullable=False, default=0)  # In cents
    wage = Column(Integer)  # Hourly wage in cents for employees
    warnings = Column(Integer, nullable=False, default=0)
    is_blacklisted = Column(Boolean, nullable=False, default=False)
    free_delivery_credits = Column(Integer, nullable=False, default=0)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
    orders = relationship("Order", back_populates="account")
    dishes_created = relationship("Dish", back_populates="chef", foreign_keys="Dish.chef_id")
    dish_reviews = relationship("DishReview", back_populates="account")


class Order(Base):
    """Customer orders"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurant.id", ondelete="RESTRICT"), nullable=False)
    order_datetime = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    final_cost = Column(Integer, nullable=False)  # Total in cents
    subtotal = Column(Integer, nullable=False)  # Before fees/discounts
    delivery_fee = Column(Integer, nullable=False, default=0)
    tip = Column(Integer, nullable=False, default=0)
    discount = Column(Integer, nullable=False, default=0)
    status = Column(order_status_enum, nullable=False, default='pending')
    delivery_address = Column(Text)
    note = Column(Text)
    is_delivery = Column(Boolean, nullable=False, default=True)
    estimated_ready_time = Column(DateTime(timezone=True))
    actual_ready_time = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="orders")
    restaurant = relationship("Restaurant", back_populates="orders")
    transactions = relationship("Transaction", back_populates="order")
    ordered_dishes = relationship("OrderedDish", back_populates="order", cascade="all, delete-orphan")
    dish_reviews = relationship("DishReview", back_populates="order")


class Dish(Base):
    """Menu items available at the restaurant"""
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True)
    restaurant_id = Column(Integer, ForeignKey("restaurant.id", ondelete="CASCADE"), nullable=False)
    chef_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Integer, nullable=False)  # In cents
    picture = Column(Text)  # Main image URL/path
    category = Column(String(100))
    is_available = Column(Boolean, nullable=False, default=True)
    is_special = Column(Boolean, nullable=False, default=False)
    average_rating = Column(Numeric(3, 2), default=0.00)
    review_count = Column(Integer, nullable=False, default=0)
    order_count = Column(Integer, nullable=False, default=0)  # Denormalized for popularity
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    restaurant = relationship("Restaurant", back_populates="dishes")
    chef = relationship("Account", back_populates="dishes_created", foreign_keys=[chef_id])
    images = relationship("DishImage", back_populates="dish", cascade="all, delete-orphan")
    reviews = relationship("DishReview", back_populates="dish", cascade="all, delete-orphan")
    ordered_dishes = relationship("OrderedDish", back_populates="dish")


class DishImage(Base):
    """Multiple images for a dish"""
    __tablename__ = "dish_images"

    id = Column(Integer, primary_key=True)
    dish_id = Column(Integer, ForeignKey("dishes.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(Text, nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    dish = relationship("Dish", back_populates="images")


class DishReview(Base):
    """Customer reviews for dishes"""
    __tablename__ = "dish_reviews"

    id = Column(Integer, primary_key=True)
    dish_id = Column(Integer, ForeignKey("dishes.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))
    rating = Column(Integer, nullable=False)  # 1-5 stars
    review_text = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    dish = relationship("Dish", back_populates="reviews")
    account = relationship("Account", back_populates="dish_reviews")
    order = relationship("Order", back_populates="dish_reviews")


class OrderedDish(Base):
    """Junction table for orders and dishes"""
    __tablename__ = "ordered_dishes"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    dish_id = Column(Integer, ForeignKey("dishes.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Integer, nullable=False)  # Price at time of order (cents)
    special_instructions = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="ordered_dishes")
    dish = relationship("Dish", back_populates="ordered_dishes")


class Transaction(Base):
    """Financial audit trail"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    transaction_type = Column(transaction_type_enum, nullable=False)
    amount = Column(Integer, nullable=False)  # In cents, positive for credit, negative for debit
    balance_before = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    description = Column(Text)
    reference_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="transactions")
    order = relationship("Order", back_populates="transactions")
