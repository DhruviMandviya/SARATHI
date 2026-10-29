from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_user
from backend.app.models.user import User
from backend.app.models.notification import Notification
from backend.app.schemas.notification import NotificationOut, NotificationListResponse, UnreadCountResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])

def _get_user_notification_filter(current_user: User):
    if current_user.role == "institution":
        return or_(
            Notification.user_id == current_user.id,
            and_(
                Notification.role == "institution",
                Notification.institution_id == current_user.institution_id
            )
        )
    else:
        # Officials, Admins, Auditors
        return or_(
            Notification.user_id == current_user.id,
            Notification.role.in_(["official", "admin", "auditor"])
        )

@router.get("", response_model=NotificationListResponse)
def list_notifications(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_filter = _get_user_notification_filter(current_user)
    
    query = db.query(Notification).filter(user_filter)
    unread_count = query.filter(Notification.is_read == False).count()
    items = query.order_by(desc(Notification.created_at)).limit(limit).all()
    
    return NotificationListResponse(items=items, unread_count=unread_count)

@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_filter = _get_user_notification_filter(current_user)
    unread_count = db.query(Notification).filter(user_filter, Notification.is_read == False).count()
    return UnreadCountResponse(unread_count=unread_count)

@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_filter = _get_user_notification_filter(current_user)
    notif = db.query(Notification).filter(user_filter, Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif

@router.post("/mark-all-read")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_filter = _get_user_notification_filter(current_user)
    updated = db.query(Notification).filter(user_filter, Notification.is_read == False).update(
        {"is_read": True}, synchronize_session="fetch"
    )
    db.commit()
    return {"message": f"Marked {updated} notifications as read", "marked_count": updated}
