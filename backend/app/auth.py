"""
Authentication and security utilities
- Password hashing with bcrypt
- JWT token generation and validation
- Security dependencies
- Rate limiting hints

SECURITY NOTES:
---------------
1. Token Blacklist: For production, implement a Redis-based token blacklist
   to support logout and token revocation. Store invalidated JTI (JWT ID) 
   claims with TTL matching token expiry.

2. Rate Limiting: Use slowapi or fastapi-limiter for rate limiting:
   - Login: 5 attempts per minute per IP
   - Register: 3 attempts per minute per IP
   - API endpoints: 100 requests per minute per user

3. Password Storage: Using bcrypt with default work factor (12).
   Consider increasing for higher security environments.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account


# ============================================================
# Configuration
# ============================================================

# Secret key for JWT signing - in production, use a proper secret from env
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dashx-dev-secret-key-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))  # 1 hour default

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer scheme for JWT
security = HTTPBearer(auto_error=False)


# ============================================================
# Password Utilities
# ============================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================
# JWT Token Utilities
# ============================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Payload data to encode (should include 'sub' for user identifier)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ============================================================
# Authentication Dependencies
# ============================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Account:
    """
    Dependency to get the current authenticated user from JWT token
    
    Raises:
        HTTPException 401 if token is missing, invalid, or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if credentials is None:
        raise credentials_exception
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise credentials_exception
    
    # Check token type
    if payload.get("type") != "access":
        raise credentials_exception
    
    # Get user email from token subject
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    # Fetch user from database
    user = db.query(Account).filter(Account.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[Account]:
    """
    Optional user authentication - returns None if no valid token
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# ============================================================
# Role-Based Access Control Dependencies
# ============================================================

def require_role(required_role: str):
    """
    Dependency factory to require a specific role
    
    Usage:
        @app.get("/admin", dependencies=[Depends(require_role("manager"))])
        def admin_endpoint(): ...
    """
    async def role_checker(current_user: Account = Depends(get_current_user)):
        if current_user.type != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )
        return current_user
    return role_checker


def require_any(allowed_roles: List[str]):
    """
    Dependency factory to require any of the specified roles
    
    Usage:
        @app.get("/kitchen", dependencies=[Depends(require_any(["chef", "manager"]))])
        def kitchen_endpoint(): ...
    """
    async def role_checker(current_user: Account = Depends(get_current_user)):
        if current_user.type not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


async def require_customer(current_user: Account = Depends(get_current_user)) -> Account:
    """
    Dependency to require customer, vip, or visitor role (ordering users)
    """
    allowed_types = ["customer", "vip", "visitor"]
    if current_user.type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Customer account required."
        )
    return current_user


async def require_employee(current_user: Account = Depends(get_current_user)) -> Account:
    """
    Dependency to require employee role (chef, delivery, or manager)
    """
    employee_types = ["chef", "delivery", "manager"]
    if current_user.type not in employee_types:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Employee account required."
        )
    return current_user


async def require_manager(current_user: Account = Depends(get_current_user)) -> Account:
    """
    Dependency to require manager role
    """
    if current_user.type != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Manager account required."
        )
    return current_user
