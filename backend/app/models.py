"""
SQLAlchemy ORM Models for DashX
Matches exactly the authoritative database schema.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Numeric, ForeignKey
)
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
    finalCost = Column(Integer, nullable=False)  # Total in cents
    status = Column(String(50), nullable=False, default='pending')
    bidID = Column(Integer, ForeignKey("bid.id", ondelete="SET NULL"), nullable=True)
    note = Column(Text, nullable=True)

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

    # Relationships
    account = relationship("Account", back_populates="delivery_rating")


class Complaint(Base):
    """Complaints table"""
    __tablename__ = "complaint"

    id = Column(Integer, primary_key=True)
    accountID = Column(Integer, ForeignKey("accounts.ID", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    filer = Column(Integer, ForeignKey("accounts.ID", ondelete="CASCADE"), nullable=False)

    # Relationships
    account = relationship("Account", back_populates="complaints_about", foreign_keys=[accountID])
    filer_account = relationship("Account", back_populates="complaints_filed", foreign_keys=[filer])


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
