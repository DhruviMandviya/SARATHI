from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    full_name: str
    institution_id: Optional[int] = None

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    institution_id: Optional[int] = None
    exp: Optional[int] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    full_name: str
    institution_id: Optional[int] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
