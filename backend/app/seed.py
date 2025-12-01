"""
Seed script for initial data
"""

from app.database import SessionLocal


def seed_data():
    """Seed minimal initial data"""
    db = SessionLocal()
    try:
        # Placeholder for seeding menu items, categories, etc.
        # Will be implemented when models are created
        print("🌱 Seeding initial data...")
        
        # Example seed data structure (to be implemented):
        # categories = [
        #     {"name": "Appetizers", "description": "Start your meal right"},
        #     {"name": "Main Courses", "description": "Hearty main dishes"},
        #     {"name": "Desserts", "description": "Sweet endings"},
        #     {"name": "Beverages", "description": "Refreshing drinks"},
        # ]
        
        print("✅ Initial data seeded successfully")
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
