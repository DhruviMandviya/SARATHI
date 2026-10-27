import pytest
from fastapi import status, Depends, APIRouter
from backend.app.core.permissions import require_official, verify_institution_access
from backend.app.main import app

# Create a test-only route to test role guards and ownership verification
rbac_router = APIRouter(prefix="/test-rbac")

@rbac_router.get("/official-only")
def official_endpoint(user = Depends(require_official)):
    return {"message": "Welcome Official", "user_id": user.id}

app.include_router(rbac_router)

def test_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inst1@aicte.gov.in", "password": "Demo@Password123"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "institution"
    assert data["institution_id"] == 1

def test_login_invalid_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inst1@aicte.gov.in", "password": "WrongPassword!"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_auth_me_authenticated(client):
    # Log in as official
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "official@aicte.gov.in", "password": "Demo@Password123"}
    )
    token = login_res.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "official@aicte.gov.in"
    assert data["role"] == "official"

def test_auth_me_unauthorized(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_rbac_official_route_allowed_for_official(client):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "official@aicte.gov.in", "password": "Demo@Password123"}
    )
    token = login_res.json()["access_token"]

    response = client.get(
        "/test-rbac/official-only",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Welcome Official"

def test_rbac_official_route_forbidden_for_institution(client):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "inst1@aicte.gov.in", "password": "Demo@Password123"}
    )
    token = login_res.json()["access_token"]

    response = client.get(
        "/test-rbac/official-only",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_institution_ownership_verification(client):
    from backend.app.models.user import User
    from fastapi import HTTPException

    # Mock user object for Institution 1
    class DummyUser:
        id = 1
        role = "institution"
        institution_id = 1

    # Accessing own institution (id=1) should not raise exception
    verify_institution_access(DummyUser(), target_institution_id=1)

    # Accessing another institution (id=2) must raise 403 HTTPException
    with pytest.raises(HTTPException) as exc_info:
        verify_institution_access(DummyUser(), target_institution_id=2)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
