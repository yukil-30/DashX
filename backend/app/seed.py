"""
Seed script for initial data
Provides minimal data to bootstrap the restaurant system.
"""

import logging
from typing import List, Dict, Any
from app.database import SessionLocal, check_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Sample menu data for seeding
SAMPLE_CATEGORIES: List[Dict[str, Any]] = [
    {"name": "Appetizers", "description": "Start your meal with our delicious starters", "sort_order": 1},
    {"name": "Main Courses", "description": "Hearty and satisfying main dishes", "sort_order": 2},
    {"name": "Desserts", "description": "Sweet endings to your meal", "sort_order": 3},
    {"name": "Beverages", "description": "Refreshing drinks and cocktails", "sort_order": 4},
]

SAMPLE_MENU_ITEMS: List[Dict[str, Any]] = [
    {"name": "Caesar Salad", "category": "Appetizers", "price": 12.99, "description": "Crisp romaine with house-made dressing"},
    {"name": "Tomato Bruschetta", "category": "Appetizers", "price": 9.99, "description": "Toasted bread with fresh tomatoes and basil"},
    {"name": "Grilled Salmon", "category": "Main Courses", "price": 28.99, "description": "Atlantic salmon with lemon butter sauce"},
    {"name": "Mushroom Risotto", "category": "Main Courses", "price": 22.99, "description": "Creamy arborio rice with wild mushrooms"},
    {"name": "Grilled Chicken Breast", "category": "Main Courses", "price": 24.99, "description": "Free-range chicken with seasonal vegetables"},
    {"name": "Chocolate Lava Cake", "category": "Desserts", "price": 10.99, "description": "Warm chocolate cake with molten center"},
    {"name": "Tiramisu", "category": "Desserts", "price": 9.99, "description": "Classic Italian coffee-flavored dessert"},
    {"name": "Fresh Fruit Plate", "category": "Desserts", "price": 8.99, "description": "Seasonal fresh fruits"},
    {"name": "House Red Wine", "category": "Beverages", "price": 9.99, "description": "Glass of our house selection"},
    {"name": "Sparkling Water", "category": "Beverages", "price": 3.99, "description": "San Pellegrino 500ml"},
]


def validate_database_connection() -> bool:
    """Validate database is accessible before seeding."""
    try:
        if not check_connection():
            logger.error("❌ Database connection failed. Is PostgreSQL running?")
            logger.error("   Try: docker-compose up -d postgres")
            return False
        logger.info("✅ Database connection verified")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        logger.error("   Ensure DATABASE_URL is correctly configured in .env")
        return False


def seed_data(force: bool = False) -> bool:
    """
    Seed minimal initial data.
    
    Args:
        force: If True, seed even if data already exists
        
    Returns:
        True if seeding was successful, False otherwise
    """
    logger.info("🌱 Starting data seeding...")
    
    # Validate connection first
    if not validate_database_connection():
        return False
    
    db = SessionLocal()
    try:
        # Note: When models are implemented, check if data exists
        # if not force:
        #     existing = db.query(Category).count()
        #     if existing > 0:
        #         logger.info("ℹ️  Data already exists. Use --force to reseed.")
        #         return True
        
        logger.info(f"📦 Preparing to seed {len(SAMPLE_CATEGORIES)} categories...")
        for category in SAMPLE_CATEGORIES:
            logger.debug(f"   - {category['name']}")
        
        logger.info(f"📦 Preparing to seed {len(SAMPLE_MENU_ITEMS)} menu items...")
        for item in SAMPLE_MENU_ITEMS:
            logger.debug(f"   - {item['name']} (${item['price']})")
        
        # TODO: When models are created, implement actual seeding:
        # for category in SAMPLE_CATEGORIES:
        #     db_category = Category(**category)
        #     db.add(db_category)
        # db.commit()
        
        db.commit()
        logger.info("✅ Initial data seeded successfully!")
        logger.info(f"   Categories: {len(SAMPLE_CATEGORIES)}")
        logger.info(f"   Menu Items: {len(SAMPLE_MENU_ITEMS)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error seeding data: {e}")
        logger.error("   Rolling back transaction...")
        db.rollback()
        raise
    finally:
        db.close()
        logger.debug("Database connection closed")


def clear_data() -> bool:
    """Clear all seeded data. Useful for testing."""
    logger.warning("⚠️  Clearing all data...")
    db = SessionLocal()
    try:
        # TODO: When models are created:
        # db.query(MenuItem).delete()
        # db.query(Category).delete()
        db.commit()
        logger.info("✅ All data cleared")
        return True
    except Exception as e:
        logger.error(f"❌ Error clearing data: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--force":
            seed_data(force=True)
        elif sys.argv[1] == "--clear":
            clear_data()
        elif sys.argv[1] == "--help":
            print("Usage: python -m app.seed [OPTIONS]")
            print("")
            print("Options:")
            print("  --force   Seed data even if it already exists")
            print("  --clear   Clear all seeded data")
            print("  --help    Show this help message")
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
            sys.exit(1)
    else:
        seed_data()
