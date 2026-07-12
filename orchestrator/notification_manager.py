import logging
from database.db import SessionLocal
from database.models import Notification
from typing import List

logger = logging.getLogger(__name__)
class NotificationManager:
    """Handles notification operations."""
    def __init__(self):
        self.db = SessionLocal()
    def create_notification(self,user_id: str,message: str,) -> Notification:
        """Create a new notification."""

        notification = Notification(
            user_id=user_id,
            message=message,
            read=False,
        )

        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        logger.info(
            "Notification created for user %s",
            user_id,
        )

        return notification

    def get_notifications(self,user_id: str,skip: int = 0,limit: int = 20,) -> List[Notification]:

        return (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def mark_as_read(self,notification_id: int,user_id: str,) -> Notification | None:
        """Mark a user's notification as read."""

        notification = (
            self.db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .first()
        )

        if notification is None:
            return None

        notification.read = True

        logger.info(
            "Notification %s marked as read",
            notification_id,
        )

        self.db.commit()
        self.db.refresh(notification)

        return notification