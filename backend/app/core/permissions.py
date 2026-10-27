from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from backend.app.models.user import User  # deferred import to avoid circular dependencies
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")
    return user

def require_roles(allowed_roles: List[str]):
    def role_checker(current_user = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {allowed_roles}, your role: {current_user.role}"
            )
        return current_user
    return role_checker

def require_official(current_user = Depends(require_roles(["official", "admin"]))):
    return current_user

def require_institution(current_user = Depends(require_roles(["institution"]))):
    return current_user

def require_admin(current_user = Depends(require_roles(["admin"]))):
    return current_user

def require_official_or_auditor(current_user = Depends(require_roles(["official", "auditor", "admin"]))):
    return current_user

def verify_institution_access(current_user, target_institution_id: int):
    """
    Enforces ownership:
    Institution users can only access their own institution.
    Officials, Admins, and Auditors have council-wide access.
    """
    if current_user.role == "institution":
        if current_user.institution_id != target_institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view or modify another institution's data."
            )
