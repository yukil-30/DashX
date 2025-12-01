"""
Tests for the health endpoint
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test cases for /health endpoint"""

    def test_health_returns_200(self):
        """Test that GET /health returns status code 200"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self):
        """Test that GET /health returns JSON with status 'ok'"""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_response_structure(self):
        """Test that health response has expected structure"""
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "version" in data
        assert "database" in data
        assert "llm_stub" in data

    def test_health_version_present(self):
        """Test that version is included in health response"""
        response = client.get("/health")
        data = response.json()
        assert data["version"] == "0.1.0"


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
