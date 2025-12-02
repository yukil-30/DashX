import os
import pytest
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db
from app.models import Account

# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_db.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    """Create database engine for tests."""
    engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL)
    
    # Enable foreign keys for SQLite
    if 'sqlite' in SQLALCHEMY_TEST_DATABASE_URL:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
            
    return engine

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Yields a database session for a test function, rolling back changes after"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="session", autouse=True)
def setup_test_db(db_engine):
    """Create tables once for the test session"""
    Base.metadata.create_all(bind=db_engine)
    yield
    # Disable foreign keys before dropping tables to avoid issues with circular dependencies
    if 'sqlite' in str(db_engine.url):
        with db_engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
            
    Base.metadata.drop_all(bind=db_engine)
    if os.path.exists("test_db.db"):
        os.remove("test_db.db")

@pytest.fixture(scope="function")
def client(db_session):
    """Yields a TestClient that uses the test database session"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass # Session is closed by fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def customer_user(db_session):
    """Create a test customer user"""
    user = Account(
        ID=100,
        email="customer@test.com",
        password="hashed_password",
        type="customer",
        balance=10000,
        warnings=0
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def restaurant(db_session):
    """Create a test restaurant"""
    restaurant = Restaurant(id=1, name='DashX Bistro', address='123 Main St')
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)
    return restaurant

@pytest.fixture
def manager_user(db_session, restaurant):
    """Create a test manager user"""
    user = Account(
        ID=103,
        email="manager@test.com",
        password="hashed_password",
        type="manager",
        balance=0,
        warnings=0,
        restaurantID=restaurant.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def chef_user(db_session, restaurant):
    """Create a test chef user"""
    user = Account(
        ID=104,
        email="chef@test.com",
        password="hashed_password",
        type="chef",
        balance=0,
        warnings=0,
        restaurantID=restaurant.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def delivery_user(db_session):
    """Create a test delivery user"""
    user = Account(
        ID=102,
        email="delivery@test.com",
        password="hashed_password",
        type="delivery",
        balance=5000,
        warnings=0
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

from app.models import Restaurant, Account, Dish, Order, Bid, OrderedDish
from datetime import datetime

@pytest.fixture(scope="function")
def seed_db(db_session):
    """Seed the database with test data using ORM"""
    # Create Restaurant
    restaurant = Restaurant(id=1, name='DashX Bistro', address='123 Main St')
    db_session.add(restaurant)
    db_session.flush()
    
    # Create Accounts
    accounts_data = [
        (1, 1, 'manager@dashxbistro.com', 'manager', 0, 0),
        (2, 1, 'chef.gordon@dashxbistro.com', 'chef', 0, 0),
        (3, 1, 'chef.julia@dashxbistro.com', 'chef', 0, 0),
        (4, 1, 'delivery.mike@dashxbistro.com', 'delivery', 0, 0),
        (5, 1, 'delivery.lisa@dashxbistro.com', 'delivery', 1, 0),
        (6, None, 'vip.john@example.com', 'vip', 0, 0),
        (7, None, 'customer.jane@example.com', 'customer', 0, 0),
        (8, None, 'customer.bob@example.com', 'customer', 0, 0),
        (9, None, 'customer.alice@example.com', 'customer', 2, 0),
        (10, None, 'customer.charlie@example.com', 'customer', 0, 0),
        (11, None, 'visitor@example.com', 'visitor', 0, 0)
    ]
    
    for acc in accounts_data:
        account = Account(
            ID=acc[0],
            restaurantID=acc[1],
            email=acc[2],
            password='hash',
            type=acc[3],
            warnings=acc[4],
            balance=1000,
            free_delivery_credits=acc[5]
        )
        db_session.add(account)
    db_session.flush()

    # Create Dishes
    for i in range(1, 6):
        dish = Dish(
            id=i,
            restaurantID=1,
            name=f'Dish {i}',
            cost=1000 + i * 100,
            reviews=0,
            average_rating=0.0
        )
        db_session.add(dish)
    db_session.flush()

    # Create Orders
    for i in range(1, 6):
        order = Order(
            id=i,
            accountID=6 + i - 1,  # Customers starting from ID 6
            finalCost=2000,
            status='pending',
            dateTime=datetime.now().isoformat()
        )
        db_session.add(order)
        
        # Add ordered dishes
        ordered_dish = OrderedDish(
            DishID=i,
            orderID=i,
            quantity=1
        )
        db_session.add(ordered_dish)
    db_session.flush()

    # Create Bids
    for i in range(1, 7):
        bid = Bid(
            id=i,
            deliveryPersonID=4,
            orderID=1 if i < 3 else 2,
            bidAmount=500
        )
        db_session.add(bid)
        
    db_session.commit()
    return db_session
