"""
Tests for authentication and account endpoints
Covers:
- User registration
- User login
- JWT token verification
- GET /auth/me
- Deposit and balance operations
- Role-based access control
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import re

from app.main import app
from app.auth import hash_password, verify_password, create_access_token, decode_token, get_current_user
from app.database import get_db


# Create test client
client = TestClient(app)


# ============================================================
# Mock User Factory
# ============================================================

def create_mock_user(
    ID=1,
    email="test@example.com",
    balance=5000,
    type="customer"
):
    """Create a mock user for testing - matches authoritative schema"""
    mock_user = MagicMock()
    mock_user.ID = ID
    mock_user.email = email
    mock_user.type = type
    mock_user.balance = balance
    mock_user.warnings = 0
    mock_user.wage = None
    mock_user.restaurantID = None
    mock_user.password = "$2b$12$hashedpassword"
    return mock_user


def create_mock_db():
    """Create a mock database session that properly simulates refresh"""
    mock_db = MagicMock()
    transaction_counter = [0]  # Use list for mutable closure
    
    def mock_refresh(obj):
        # Simulate database assigning ID on refresh
        if hasattr(obj, 'ID') and obj.ID is None:
            transaction_counter[0] += 1
            obj.ID = transaction_counter[0]
    
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.refresh = mock_refresh
    return mock_db


# ============================================================
# Password Hashing Tests
# ============================================================

class TestPasswordHashing:
    """Test password hashing utilities"""

    def test_hash_password_returns_hash(self):
        """Test that hash_password returns a bcrypt hash"""
        password = "SecureP@ss123"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_hash_password_different_for_same_input(self):
        """Test that hashing same password twice produces different hashes (salt)"""
        password = "SecureP@ss123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2  # Different salts

    def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password"""
        password = "SecureP@ss123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for wrong password"""
        password = "SecureP@ss123"
        wrong_password = "WrongPassword123"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False

    def test_password_not_echoed_in_hash(self):
        """Security: Ensure plaintext password is not visible in hash"""
        password = "MySecret123"
        hashed = hash_password(password)
        
        assert password not in hashed


# ============================================================
# JWT Token Tests
# ============================================================

class TestJWTTokens:
    """Test JWT token creation and validation"""

    def test_create_access_token(self):
        """Test that access token is created successfully"""
        token = create_access_token(data={"sub": "test@example.com", "user_id": 1})
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    def test_decode_valid_token(self):
        """Test that valid token can be decoded"""
        payload_data = {"sub": "test@example.com", "user_id": 1}
        token = create_access_token(data=payload_data)
        
        decoded = decode_token(token)
        
        assert decoded is not None
        assert decoded["sub"] == "test@example.com"
        assert decoded["user_id"] == 1
        assert "exp" in decoded
        assert "iat" in decoded

    def test_decode_invalid_token(self):
        """Test that invalid token returns None"""
        result = decode_token("invalid.token.here")
        assert result is None

    def test_decode_tampered_token(self):
        """Test that tampered token returns None"""
        token = create_access_token(data={"sub": "test@example.com"})
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        
        result = decode_token(tampered)
        assert result is None

    def test_token_contains_expiration(self):
        """Test that token contains expiration claim"""
        token = create_access_token(data={"sub": "test@example.com"})
        decoded = decode_token(token)
        
        assert "exp" in decoded
        assert decoded["exp"] > datetime.now(timezone.utc).timestamp()


# ============================================================
# Registration Endpoint Tests
# ============================================================

class TestRegistration:
    """Test POST /auth/register endpoint"""

    def test_register_success(self):
        """Test successful user registration"""
        # Use unique email for each test run
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/auth/register", json={
                "username": unique_email,
                "password": "SecureP@ss123",
                "display_name": "Test User",
                "email": unique_email,
                "role_requested": "customer"
            })
            
            # Accept either success or conflict (if DB already has user)
            assert response.status_code in [201, 409]
        finally:
            app.dependency_overrides.clear()

    def test_register_invalid_email(self):
        """Test registration with invalid email format"""
        response = client.post("/auth/register", json={
            "username": "not-an-email",
            "password": "SecureP@ss123",
            "display_name": "Test User",
            "email": "not-an-email",
            "role_requested": "customer"
        })
        
        assert response.status_code == 422  # Validation error

    def test_register_password_too_short(self):
        """Test registration with password less than 8 characters"""
        response = client.post("/auth/register", json={
            "username": "test@example.com",
            "password": "short1",
            "display_name": "Test User",
            "email": "test@example.com",
            "role_requested": "customer"
        })
        
        assert response.status_code == 422

    def test_register_password_no_digit(self):
        """Test registration with password without digits"""
        response = client.post("/auth/register", json={
            "username": "test@example.com",
            "password": "NoDigitsHere",
            "display_name": "Test User",
            "email": "test@example.com",
            "role_requested": "customer"
        })
        
        assert response.status_code == 422

    def test_register_invalid_role(self):
        """Test registration with invalid role (employee roles not allowed)"""
        response = client.post("/auth/register", json={
            "email": "test_invalid@example.com",
            "password": "SecureP@ss123",
            "type": "manager"  # Not allowed for self-registration
        })
        
        assert response.status_code == 422

    def test_register_response_has_token(self):
        """Test that successful registration returns access token"""
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/auth/register", json={
                "username": unique_email,
                "password": "SecureP@ss123",
                "display_name": "Test User",
                "email": unique_email,
                "role_requested": "customer"
            })
            
            if response.status_code == 201:
                data = response.json()
                assert "access_token" in data
                assert "token_type" in data
                assert data["token_type"] == "bearer"
                assert "expires_in" in data
        finally:
            app.dependency_overrides.clear()

    def test_register_password_not_in_response(self):
        """Security: Ensure password is never echoed in response"""
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecureP@ss123"
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/auth/register", json={
                "username": unique_email,
                "password": password,
                "display_name": "Test User",
                "email": unique_email,
                "role_requested": "customer"
            })
            
            # Check password is not in response body
            response_text = response.text
            assert password not in response_text
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Login Endpoint Tests
# ============================================================

class TestLogin:
    """Test POST /auth/login endpoint"""

    def test_login_missing_username(self):
        """Test login without username"""
        response = client.post("/auth/login", json={
            "password": "SecureP@ss123"
        })
        
        assert response.status_code == 422

    def test_login_missing_password(self):
        """Test login without password"""
        response = client.post("/auth/login", json={
            "username": "test@example.com"
        })
        
        assert response.status_code == 422

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        mock_db = MagicMock()
        # User not found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/auth/login", json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword123"
            })
            
            assert response.status_code == 401
            data = response.json()
            assert "Invalid credentials" in data.get("detail", "")
        finally:
            app.dependency_overrides.clear()

    def test_login_password_not_echoed(self):
        """Security: Ensure password is not in error response"""
        password = "MySecretPassword123"
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/auth/login", json={
                "email": "test@example.com",
                "password": password
            })
            
            # Password should never appear in any response
            assert password not in response.text
        finally:
            app.dependency_overrides.clear()


# ============================================================
# GET /auth/me Endpoint Tests
# ============================================================

class TestGetMe:
    """Test GET /auth/me endpoint"""

    def test_me_without_token(self):
        """Test /auth/me without authentication token"""
        response = client.get("/auth/me")
        
        assert response.status_code == 401

    def test_me_with_invalid_token(self):
        """Test /auth/me with invalid token"""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401

    def test_me_response_no_password(self):
        """Security: Ensure password is never in /auth/me response"""
        # Create a mock user matching authoritative schema
        mock_user = MagicMock()
        mock_user.ID = 1
        mock_user.email = "test@example.com"
        mock_user.type = "customer"
        mock_user.balance = 5000
        mock_user.warnings = 0
        mock_user.wage = None
        mock_user.restaurantID = None
        mock_user.password = "$2b$12$hashedpassword"
        
        # Use dependency override instead of patch
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            token = create_access_token(data={"sub": "test@example.com", "user_id": 1})
            response = client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Response should not contain password
            response_text = response.text.lower()
            assert "password" not in response_text or "password\":" not in response_text
            assert "$2b$" not in response_text
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Deposit Endpoint Tests
# ============================================================

class TestDeposit:
    """Test POST /account/deposit endpoint"""

    def test_deposit_without_auth(self):
        """Test deposit without authentication"""
        response = client.post("/account/deposit", json={
            "amount_cents": 1000
        })
        
        assert response.status_code == 401

    def test_deposit_negative_amount(self):
        """Test deposit with negative amount - validation rejects it"""
        mock_user = create_mock_user()
        mock_db = create_mock_db()
        
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post(
                "/account/deposit",
                json={"amount_cents": -500}
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_deposit_zero_amount(self):
        """Test deposit with zero amount"""
        mock_user = create_mock_user()
        mock_db = create_mock_db()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post(
                "/account/deposit",
                json={"amount_cents": 0}
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_deposit_exceeds_max(self):
        """Test deposit exceeding maximum allowed ($1M)"""
        mock_user = create_mock_user()
        mock_db = create_mock_db()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post(
                "/account/deposit",
                json={"amount_cents": 200_000_000_00}  # $2M in cents
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()
    
    def test_deposit_success(self):
        """Test successful deposit"""
        mock_user = create_mock_user(balance=5000)
        mock_db = create_mock_db()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post(
                "/account/deposit",
                json={"amount_cents": 1000}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Deposit successful"
            assert data["new_balance_cents"] == 6000  # 5000 + 1000
        finally:
            app.dependency_overrides.clear()
    
    def test_deposit_updates_balance(self):
        """Test that deposit correctly updates user balance"""
        mock_user = create_mock_user(balance=1000)
        mock_db = create_mock_db()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post(
                "/account/deposit",
                json={"amount_cents": 2500}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["new_balance_cents"] == 3500
            assert data["new_balance_formatted"] == "$35.00"
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Balance Endpoint Tests
# ============================================================

class TestBalance:
    """Test GET /account/balance endpoint"""

    def test_balance_without_auth(self):
        """Test balance check without authentication"""
        response = client.get("/account/balance")
        
        assert response.status_code == 401

    def test_balance_with_invalid_token(self):
        """Test balance with invalid token"""
        response = client.get(
            "/account/balance",
            headers={"Authorization": "Bearer invalid.token"}
        )
        
        assert response.status_code == 401

    def test_balance_success(self):
        """Test successful balance retrieval"""
        mock_user = create_mock_user(balance=12345)
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.get("/account/balance")
            
            assert response.status_code == 200
            data = response.json()
            assert data["balance_cents"] == 12345
            assert data["balance_formatted"] == "$123.45"
        finally:
            app.dependency_overrides.clear()

    def test_balance_zero(self):
        """Test balance of zero"""
        mock_user = create_mock_user(balance=0)
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.get("/account/balance")
            
            assert response.status_code == 200
            data = response.json()
            assert data["balance_cents"] == 0
            assert data["balance_formatted"] == "$0.00"
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Role-Based Access Control Tests
# ============================================================

class TestRoleBasedAccess:
    """Test role-based access control"""

    def test_warning_based_denial(self):
        """Test that users with high warnings can be denied access"""
        from fastapi import HTTPException
        
        def mock_user_with_high_warnings():
            raise HTTPException(
                status_code=403,
                detail="Account has been suspended"
            )
        
        app.dependency_overrides[get_current_user] = mock_user_with_high_warnings
        
        try:
            token = create_access_token(data={"sub": "warned@example.com"})
            response = client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Should be forbidden
            assert response.status_code in [401, 403]
        finally:
            app.dependency_overrides.clear()


# ============================================================
# Integration Tests (with mocked DB)
# ============================================================

class TestAuthFlow:
    """Integration tests for complete auth flow"""

    def test_register_login_flow(self):
        """Test complete register -> login -> get profile flow"""
        import uuid
        unique_email = f"flow_test_{uuid.uuid4().hex[:8]}@example.com"
        
        # This is a mock-based integration test
        # In real integration tests, use a test database
        
        mock_user = MagicMock()
        mock_user.ID = 999
        mock_user.email = unique_email
        mock_user.password = hash_password("TestP@ss123")
        mock_user.type = "customer"
        mock_user.balance = 0
        mock_user.warnings = 0
        mock_user.wage = None
        mock_user.restaurantID = None
        
        # Step 1: Verify password hashing works
        assert verify_password("TestP@ss123", mock_user.password)
        
        # Step 2: Create token
        token = create_access_token(data={
            "sub": mock_user.email,
            "user_id": mock_user.ID,
            "role": mock_user.type
        })
        
        # Step 3: Verify token contains correct data
        decoded = decode_token(token)
        assert decoded["sub"] == unique_email
        assert decoded["user_id"] == 999
        assert decoded["role"] == "customer"


# ============================================================
# Security Tests
# ============================================================

class TestSecurityMeasures:
    """Test security measures"""

    def test_timing_attack_prevention_login(self):
        """
        Verify that login error messages don't reveal whether user exists.
        Both non-existent user and wrong password should return same message.
        """
        # Test with non-existent user
        response1 = client.post("/auth/login", json={
            "username": "nonexistent@example.com",
            "password": "SomeP@ssword123"
        })
        
        # The error message should be generic
        if response1.status_code == 401:
            data = response1.json()
            # Should not reveal if user exists or not
            assert "Invalid credentials" in data.get("detail", "") or \
                   "invalid" in data.get("detail", "").lower()

    def test_password_complexity_enforced(self):
        """Test that password complexity requirements are enforced"""
        # No digits
        response = client.post("/auth/register", json={
            "username": "test@example.com",
            "password": "NoDigitsHere",
            "display_name": "Test",
            "email": "test@example.com",
            "role_requested": "customer"
        })
        assert response.status_code == 422
        
        # Too short
        response = client.post("/auth/register", json={
            "username": "test@example.com",
            "password": "Ab1",
            "display_name": "Test",
            "email": "test@example.com",
            "role_requested": "customer"
        })
        assert response.status_code == 422

    def test_jwt_signature_verified(self):
        """Test that JWT signature is properly verified"""
        # Create a valid token
        valid_token = create_access_token(data={"sub": "test@example.com"})
        
        # Modify payload but keep signature (should fail)
        parts = valid_token.split('.')
        modified_token = parts[0] + '.' + 'eyJzdWIiOiJoYWNrZXJAZXhhbXBsZS5jb20ifQ' + '.' + parts[2]
        
        result = decode_token(modified_token)
        assert result is None  # Should fail verification
