from typing import Union
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import verify_password, create_access_token
from backend.app.core.permissions import get_current_user
from backend.app.models.user import User
from backend.app.models.audit import AuditLog
from backend.app.schemas.auth import Token, UserOut, LoginRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    db: Session = Depends(get_db)
):
    # Support both JSON payload and OAuth2 form-data
    email = None
    password = None

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        email = body.get("email") or body.get("username")
        password = body.get("password")
    else:
        form = await request.form()
        email = form.get("username") or form.get("email")
        password = form.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact administrator."
        )

    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        institution_id=user.institution_id
    )

    # Log successful login to audit trail
    audit_entry = AuditLog(
        actor_id=user.id,
        actor_role=user.role,
        action="user_login",
        entity_type="user",
        entity_id=user.id,
        before_state=None,
        after_state={"ip": request.client.host if request.client else "unknown"}
    )
    db.add(audit_entry)
    db.commit()

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        institution_id=user.institution_id
    )

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
