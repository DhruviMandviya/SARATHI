from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class NotificationOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    role: Optional[str] = None
    institution_id: Optional[int] = None
    title: str
    message: str
    category: str
    link: Optional[str] = None
    is_read: bool
    application_id: Optional[int] = None
    reference_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationListResponse(BaseModel):
    items: List[NotificationOut]
    unread_count: int

class UnreadCountResponse(BaseModel):
    unread_count: int
