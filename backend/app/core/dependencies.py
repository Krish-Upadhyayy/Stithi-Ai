"""FastAPI authentication and authorization dependencies."""

from typing import List, Callable, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jwt.exceptions import PyJWTError

from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.models.user import User

# HTTP Bearer scheme for OpenAPI documentation and token extraction
security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validates JWT bearer token and retrieves authenticated user from database.
    
    Raises:
        HTTPException 401 if token is missing, expired, invalid, or user not found.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_authenticated_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency verifying that the user is authenticated."""
    return current_user


def require_role(allowed_roles: List[str]) -> Callable:
    """Dependency factory enforcing role-based access control.
    
    Example:
        @router.get("/admin-only", dependencies=[Depends(require_role(["ADMIN"]))])
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: User role '{current_user.role}' lacks required permission.",
            )
        return current_user

    return role_checker


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Optionally resolves the current user without failing if unauthenticated."""
    if not credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None

