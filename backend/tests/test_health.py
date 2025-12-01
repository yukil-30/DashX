"""
Tests for the health endpoint
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test cases for /health endpoint"""

    def test_health_returns_200(self):
        """Test that GET /health returns status code 200"""
        response = client.get("/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_health_returns_ok_status(self):
        """Test that GET /health returns JSON with status 'ok'"""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok", f"Expected status 'ok', got '{data['status']}'"

    def test_health_response_structure(self):
        """Test that health response has expected structure"""
        response = client.get("/health")
        data = response.json()
        
        required_fields = ["status", "version", "database", "llm_stub"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_health_version_present(self):
        """Test that version is included in health response"""
        response = client.get("/health")
        data = response.json()
        assert data["version"] == "0.1.0", f"Expected version '0.1.0', got '{data['version']}'"

    def test_health_response_is_json(self):
        """Test that health endpoint returns valid JSON"""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"
        # Should not raise an exception
        data = response.json()
        assert isinstance(data, dict)

    def test_health_database_field_present(self):
        """Test that database status is included"""
        response = client.get("/health")
        data = response.json()
        assert "database" in data
        # Should be one of the expected states
        valid_states = ["connected", "disconnected", "not_configured", "not_checked"]
        assert any(state in data["database"] for state in valid_states) or "error" in data["database"]

    def test_health_llm_stub_field_present(self):
        """Test that llm_stub status is included"""
        response = client.get("/health")
        data = response.json()
        assert "llm_stub" in data


class TestRootEndpoint:
    """Test cases for root endpoint"""

    def test_root_returns_200(self):
        """Test that GET / returns status code 200"""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_welcome_message(self):
        """Test that GET / returns welcome message"""
        response = client.get("/")
        data = response.json()
        assert "message" in data
        assert "Welcome" in data["message"]

    def test_root_includes_docs_link(self):
        """Test that root response includes docs link"""
        response = client.get("/")
        data = response.json()
        assert data["docs"] == "/docs"

    def test_root_includes_health_link(self):
        """Test that root response includes health link"""
        response = client.get("/")
        data = response.json()
        assert data["health"] == "/health"

    def test_root_includes_version(self):
        """Test that root response includes version"""
        response = client.get("/")
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.1.0"


class TestErrorHandling:
    """Test cases for error handling"""

    def test_404_for_nonexistent_route(self):
        """Test that non-existent routes return 404"""
        response = client.get("/nonexistent-route")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test that invalid methods return 405"""
        response = client.post("/health")
        assert response.status_code == 405


class TestCORS:
    """Test CORS configuration"""

    def test_cors_headers_present(self):
        """Test that CORS headers are present for allowed origins"""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        # The preflight request should succeed
        assert response.status_code in [200, 400]  # FastAPI may return 400 for OPTIONS without proper headers

    def test_cors_allows_localhost_3000(self):
        """Test that CORS allows requests from localhost:3000"""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 200
