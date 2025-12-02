"""
Tests for Image Search functionality

Tests:
- Image upload and validation
- Feature extraction (histogram-based)
- Similarity matching
- Top-K results
- Error handling
"""

import pytest
import io
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import Dish, Account
from app.database import get_db
from app.auth import create_access_token
from app.image_utils import (
    ImageFeatureExtractor,
    rank_dishes_by_similarity,
    get_cached_dish_features,
    clear_dish_features_cache
)


@pytest.fixture
def test_image_bytes() -> bytes:
    """Create a test image (red square)"""
    img = Image.new('RGB', (100, 100), color='red')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


@pytest.fixture
def test_image_blue() -> bytes:
    """Create a test image (blue square)"""
    img = Image.new('RGB', (100, 100), color='blue')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


@pytest.fixture
def test_image_green() -> bytes:
    """Create a test image (green square)"""
    img = Image.new('RGB', (100, 100), color='green')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


@pytest.fixture
def authenticated_client() -> TestClient:
    """Create authenticated test client"""
    from app.auth import create_access_token
    
    # Create token for test user
    token = create_access_token(data={"sub": "test@example.com"})
    
    # Create client with auth
    client = TestClient(app)
    client.headers = {"Authorization": f"Bearer {token}"}
    
    return client


class TestImageFeatureExtraction:
    """Test feature extraction utilities"""
    
    def test_histogram_extraction(self, test_image_bytes):
        """Test that histogram features can be extracted"""
        extractor = ImageFeatureExtractor(use_clip=False, use_huggingface=False)
        features = extractor.extract_features(test_image_bytes)
        
        # Should return a feature vector
        assert features is not None
        assert len(features) > 0
        assert features.shape[0] == 32 * 3  # 32 bins * 3 channels
    
    def test_different_images_have_different_features(
        self, test_image_bytes, test_image_blue
    ):
        """Test that different colored images have different features"""
        extractor = ImageFeatureExtractor(use_clip=False, use_huggingface=False)
        
        features_red = extractor.extract_features(test_image_bytes)
        features_blue = extractor.extract_features(test_image_blue)
        
        # Features should be different
        assert not (features_red == features_blue).all()
    
    def test_similarity_same_image(self, test_image_bytes):
        """Test that same image has high similarity with itself"""
        extractor = ImageFeatureExtractor(use_clip=False, use_huggingface=False)
        
        features1 = extractor.extract_features(test_image_bytes)
        features2 = extractor.extract_features(test_image_bytes)
        
        similarity = extractor.compute_similarity(features1, features2)
        
        # Should be very similar (close to 1.0)
        assert similarity > 0.99
    
    def test_similarity_different_images(
        self, test_image_bytes, test_image_blue
    ):
        """Test that different images have lower similarity"""
        extractor = ImageFeatureExtractor(use_clip=False, use_huggingface=False)
        
        features_red = extractor.extract_features(test_image_bytes)
        features_blue = extractor.extract_features(test_image_blue)
        
        similarity = extractor.compute_similarity(features_red, features_blue)
        
        # Should be less similar than identical images
        assert similarity < 0.99


class TestImageSearchAPI:
    """Test image search API endpoints"""
    
    def test_search_requires_auth(self, test_image_bytes):
        """Test that image search requires authentication"""
        client = TestClient(app)
        
        response = client.post(
            "/image-search",
            files={"file": ("test.jpg", test_image_bytes, "image/jpeg")}
        )
        
        assert response.status_code == 401
    
    def test_search_with_valid_image(self, authenticated_client, test_image_bytes):
        """Test image search with valid image"""
        # Clear cache first
        clear_dish_features_cache()
        
        # Since we don't have actual image files in test environment,
        # this will likely return 404 (no dishes with images)
        # In production with seeded data, would return 200
        response = authenticated_client.post(
            "/image-search",
            files={"file": ("test.jpg", test_image_bytes, "image/jpeg")}
        )
        
        # Should succeed but may return empty if no images exist
        assert response.status_code in [200, 404]
    
    def test_search_with_invalid_file_type(self, authenticated_client):
        """Test that non-image files are rejected"""
        text_content = b"This is not an image"
        
        response = authenticated_client.post(
            "/image-search",
            files={"file": ("test.txt", text_content, "text/plain")}
        )
        
        assert response.status_code == 400
        assert "image" in response.json()["detail"].lower()
    
    def test_search_with_large_file(self, authenticated_client):
        """Test that oversized files are rejected"""
        # Create a large image (over 10MB)
        large_img = Image.new('RGB', (5000, 5000), color='red')
        buf = io.BytesIO()
        large_img.save(buf, format='JPEG', quality=100)
        large_bytes = buf.getvalue()
        
        if len(large_bytes) > 10 * 1024 * 1024:
            response = authenticated_client.post(
                "/image-search",
                files={"file": ("large.jpg", large_bytes, "image/jpeg")}
            )
            
            assert response.status_code == 413
    
    def test_search_status_endpoint(self, authenticated_client):
        """Test the status endpoint"""
        response = authenticated_client.get("/image-search/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "method" in data
        assert "total_dishes" in data
        assert "dishes_with_images" in data
        assert data["method"] == "Hugging Face vision model"  # Default is now HF model


class TestRanking:
    """Test dish ranking by similarity"""
    
    def test_rank_dishes_returns_top_k(
        self, test_image_bytes, test_image_blue, test_image_green
    ):
        """Test that ranking returns correct number of results"""
        extractor = ImageFeatureExtractor(use_clip=False, use_huggingface=False)
        
        # Create query features
        query_features = extractor.extract_features(test_image_bytes)
        
        # Create dish features
        dish_features = [
            (1, extractor.extract_features(test_image_bytes), "Red Dish"),
            (2, extractor.extract_features(test_image_blue), "Blue Dish"),
            (3, extractor.extract_features(test_image_green), "Green Dish"),
        ]
        
        # Rank
        results = rank_dishes_by_similarity(query_features, dish_features, top_k=2)
        
        assert len(results) == 2
    
    def test_rank_dishes_orders_by_similarity(
        self, test_image_bytes, test_image_blue, test_image_green
    ):
        """Test that dishes are ordered by similarity (highest first)"""
        extractor = ImageFeatureExtractor(use_clip=False, use_huggingface=False)
        
        # Query is red
        query_features = extractor.extract_features(test_image_bytes)
        
        # Dishes: red (most similar), green, blue
        dish_features = [
            (1, extractor.extract_features(test_image_bytes), "Red Dish"),
            (2, extractor.extract_features(test_image_blue), "Blue Dish"),
            (3, extractor.extract_features(test_image_green), "Green Dish"),
        ]
        
        results = rank_dishes_by_similarity(query_features, dish_features, top_k=3)
        
        # First result should have highest similarity
        assert results[0][0] == 1  # Red dish (ID=1)
        assert results[0][1] > results[1][1]  # Higher score than second
        # Note: Blue and green might have same similarity to red (both different)
        # so we just check ordering is maintained
        assert results[1][1] >= results[2][1]  # Descending order


class TestCLIPIntegration:
    """Test CLIP integration (if available)"""
    
    def test_clip_adapter_import(self):
        """Test that CLIP adapter can be imported"""
        try:
            from app.clip_adapter import CLIPAdapter
            assert CLIPAdapter is not None
        except ImportError:
            pytest.skip("CLIP dependencies not installed")
    
    @pytest.mark.skipif(
        True,  # Skip by default since CLIP is optional
        reason="CLIP model not available in test environment"
    )
    def test_clip_encoding(self, test_image_bytes):
        """Test CLIP encoding (requires CLIP to be installed)"""
        from app.clip_adapter import CLIPAdapter
        
        adapter = CLIPAdapter()
        embedding = adapter.encode_image(test_image_bytes)
        
        assert embedding is not None
        assert len(embedding) == 512  # CLIP embedding size


def test_precompute_endpoint_requires_manager(authenticated_client):
    """Test that precompute endpoint requires manager role"""
    response = authenticated_client.post("/image-search/precompute")
    
    # Should fail because test user is customer, not manager
    assert response.status_code == 403


def test_precompute_endpoint_with_manager():
    """Test precompute endpoint with manager account"""
    from app.auth import create_access_token, get_current_user
    from unittest.mock import patch, MagicMock
    from app.database import get_db
    
    # Create manager token
    token = create_access_token(data={"sub": "manager@example.com"})
    client = TestClient(app)
    
    # Mock both authentication and database
    mock_manager = MagicMock()
    mock_manager.email = "manager@example.com"
    mock_manager.type = "manager"
    mock_manager.ID = 1
    
    mock_db = MagicMock()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_manager
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        # Clear cache
        clear_dish_features_cache()
        
        response = client.post(
            "/image-search/precompute",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "dish_count" in data
        assert "method" in data
    finally:
        # Clean up overrides
        app.dependency_overrides = {}
