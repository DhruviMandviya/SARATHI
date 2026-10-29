from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.models.notification import Notification
from backend.app.models.user import User

def create_notification(
    db: Session,
    title: str,
    message: str,
    category: str,
    user_id: Optional[int] = None,
    role: Optional[str] = None,
    institution_id: Optional[int] = None,
    application_id: Optional[int] = None,
    link: Optional[str] = None,
    reference_id: Optional[str] = None
) -> Notification:
    """
    Persists a genuine database notification.
    Enforces that notification badges and lists are 100% backend-driven.
    """
    notification = Notification(
        user_id=user_id,
        role=role,
        institution_id=institution_id,
        title=title,
        message=message,
        category=category,
        link=link,
        is_read=False,
        application_id=application_id,
        reference_id=reference_id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification

def notify_institution(
    db: Session,
    institution_id: int,
    title: str,
    message: str,
    category: str,
    application_id: Optional[int] = None,
    link: Optional[str] = None,
    reference_id: Optional[str] = None
):
    """Notifies all authorized users of an institution or creates an institution-targeted notification."""
    return create_notification(
        db=db,
        title=title,
        message=message,
        category=category,
        role="institution",
        institution_id=institution_id,
        application_id=application_id,
        link=link,
        reference_id=reference_id
    )

def notify_officials(
    db: Session,
    title: str,
    message: str,
    category: str,
    application_id: Optional[int] = None,
    link: Optional[str] = None,
    reference_id: Optional[str] = None
):
    """Notifies all council scrutiny officials."""
    return create_notification(
        db=db,
        title=title,
        message=message,
        category=category,
        role="official",
        application_id=application_id,
        link=link,
        reference_id=reference_id
    )
