"""Authentication router for SIH Training Centre AI Monitoring System."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import verify_password, create_access_token
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.schemas.user import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, summary="User Authentication Login")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates user with email and password.
    
    Returns signed JWT access token and public user profile.
    Never returns password or password hash.
    """
    user = db.query(User).filter(User.email == login_data.email).first()

    # Generic credential check prevents account enumeration
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue signed JWT with subject as user.id and role claim
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse, summary="Get Current Authenticated User")
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the profile of the currently authenticated user based on JWT bearer token."""
    return UserResponse.model_validate(current_user)
