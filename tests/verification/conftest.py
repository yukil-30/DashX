"""
Pytest Configuration for Verification Tests
"""
import pytest
import asyncio
import os


# Set test environment variables
os.environ.setdefault("DATABASE_URL", "postgresql://restaurant_user:restaurant_password@localhost:5432/restaurant_db")
os.environ.setdefault("BACKEND_URL", "http://localhost:8000")
os.environ.setdefault("USE_MOCK_LLM", "true")
os.environ.setdefault("USE_MOCK_STT", "true")
os.environ.setdefault("USE_MOCK_NLP", "true")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def unwrap_user_response(data):
    """Helper to unwrap user data from API responses
    
    Some endpoints return {"user": {...}}, others return {...} directly.
    This helper handles both cases.
    """
    if isinstance(data, dict) and "user" in data:
        return data["user"]
    return data


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")


def pytest_collection_modifyitems(config, items):
    """Add markers to tests automatically"""
    for item in items:
        # Mark all verification tests as integration
        if "verification" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Mark e2e test specifically
        if "end_to_end" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)
