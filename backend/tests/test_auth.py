"""Authentication and authorization test suite."""

import pytest
from fastapi import Depends
from backend.app.models.user import User
from backend.app.core.security import get_password_hash, create_access_token
from backend.app.core.dependencies import require_role
from backend.app.main import app


# Test helper endpoint for role checking (named handle_* to avoid pytest collection)
@app.get("/api/v1/test/admin-only", dependencies=[Depends(require_role(["ADMIN"]))])
def handle_admin_only_route():
    return {"message": "Admin authorized"}


@app.get("/api/v1/test/reviewer-only", dependencies=[Depends(require_role(["REVIEWER"]))])
def handle_reviewer_only_route():
    return {"message": "Reviewer authorized"}


@pytest.fixture
def test_users(db_session):
    """Creates test users with hashed passwords and distinct roles."""
    admin = User(
        name="Admin User",
        email="admin@test.gov.in",
        password_hash=get_password_hash("CorrectPassword123!"),
        role="ADMIN",
    )
    centre_user = User(
        name="Centre User",
        email="centre@test.gov.in",
        password_hash=get_password_hash("CentrePassword123!"),
        role="CENTRE_USER",
    )
    reviewer = User(
        name="Reviewer User",
        email="reviewer@test.gov.in",
        password_hash=get_password_hash("ReviewerPassword123!"),
        role="REVIEWER",
    )
    db_session.add_all([admin, centre_user, reviewer])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(centre_user)
    db_session.refresh(reviewer)
    return {"admin": admin, "centre_user": centre_user, "reviewer": reviewer}


# 1. Successful login
def test_successful_login(client, test_users):
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@test.gov.in",
        "password": "CorrectPassword123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@test.gov.in"
    assert data["user"]["role"] == "ADMIN"


# 2. Invalid password
def test_login_invalid_password(client, test_users):
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@test.gov.in",
        "password": "WrongPassword!",
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


# 3. Unknown user
def test_login_unknown_user(client, test_users):
    response = client.post("/api/v1/auth/login", json={
        "email": "nonexistent@test.gov.in",
        "password": "AnyPassword123!",
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


# 4. Missing token on protected endpoint
def test_auth_me_missing_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "token is missing" in response.json()["detail"].lower()


# 5. Invalid token on protected endpoint
def test_auth_me_invalid_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.payload"}
    )
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]


# 6. Valid token resolution
def test_valid_token_resolution(client, test_users):
    token = create_access_token(data={"sub": test_users["admin"].id, "role": "ADMIN"})
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "admin@test.gov.in"


# 7. /auth/me with valid authentication
def test_auth_me_authenticated(client, test_users):
    login_res = client.post("/api/v1/auth/login", json={
        "email": "centre@test.gov.in",
        "password": "CentrePassword123!",
    })
    token = login_res.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    user_info = response.json()
    assert user_info["email"] == "centre@test.gov.in"
    assert user_info["role"] == "CENTRE_USER"


# 8. /auth/me without authentication
def test_auth_me_unauthenticated(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


# 9. Role dependency behavior (Admin route forbidden to Centre User)
def test_role_dependency_authorization(client, test_users):
    # Log in as Centre User
    centre_login = client.post("/api/v1/auth/login", json={
        "email": "centre@test.gov.in",
        "password": "CentrePassword123!",
    })
    centre_token = centre_login.json()["access_token"]

    # Try accessing admin-only route -> Should fail with 403 Forbidden
    forbidden_res = client.get(
        "/api/v1/test/admin-only",
        headers={"Authorization": f"Bearer {centre_token}"}
    )
    assert forbidden_res.status_code == 403
    assert "lacks required permission" in forbidden_res.json()["detail"]

    # Log in as Admin
    admin_login = client.post("/api/v1/auth/login", json={
        "email": "admin@test.gov.in",
        "password": "CorrectPassword123!",
    })
    admin_token = admin_login.json()["access_token"]

    # Try accessing admin-only route -> Should succeed with 200 OK
    admin_res = client.get(
        "/api/v1/test/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_res.status_code == 200
    assert admin_res.json()["message"] == "Admin authorized"


# 10. Password and password hash are NEVER returned in API responses
def test_password_hash_never_returned(client, test_users):
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@test.gov.in",
        "password": "CorrectPassword123!",
    })
    login_data = login_res.json()
    assert "password" not in login_data["user"]
    assert "password_hash" not in login_data["user"]

    token = login_data["access_token"]
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    me_data = me_res.json()
    assert "password" not in me_data
    assert "password_hash" not in me_data
