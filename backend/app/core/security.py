"""Security, password hashing, and JWT token management.

Strict rules:
- No plain-text passwords stored.
- JWT secrets loaded from settings/environment.
- Bcrypt password hashing.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
import bcrypt
import jwt
from jwt.exceptions import PyJWTError

from backend.app.core.config import settings


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CENTRE_USER = "CENTRE_USER"
    REVIEWER = "REVIEWER"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Generates bcrypt hash for a plain password."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed JWT access token.
    
    Ensures RFC 7519 compliance (sub claim must be a string).
    """
    to_encode = data.copy()
    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a signed JWT access token.
    
    Raises:
        PyJWTError on expiration or invalid signature.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
