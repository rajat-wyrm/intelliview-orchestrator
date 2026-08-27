import logging

from sqlalchemy.orm import Session

from database.db import SessionLocal
from database.models import Notification

logger = logging.getLogger(__name__)


class NotificationManager:
    """Handles notification operations."""

    SCHEDULE_STATUS_MESSAGES = {
        "cancelled": "Your interview schedule has been cancelled.",
        "rescheduled": "Your interview schedule has been rescheduled.",
    }

    def __init__(self, db: Session | None = None):
        """
        Initialize the notification manager.

        A database session can be supplied by the caller so that notification
        operations use the same transaction/session as the originating request.
        If no session is supplied, a new SessionLocal session is created for
        backwards compatibility.
        """
        self.db = db or SessionLocal()

    def create_notification(
        self,
        user_id: str,
        message: str,
    ) -> Notification:
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

    def notify_schedule_status_change(
        self,
        user_id: str,
        new_status: str,
    ) -> Notification | None:
        """
        Create a notification for a supported interview schedule status change.

        Only cancelled and rescheduled statuses generate notifications.
        Returns None for statuses that do not require a notification.
        """

        clean_status = new_status.strip().lower()

        message = self.SCHEDULE_STATUS_MESSAGES.get(clean_status)

        if message is None:
            logger.debug(
                "No notification required for schedule status '%s'",
                clean_status,
            )
            return None

        logger.info(
            "Creating schedule status notification: user=%s, status=%s",
            user_id,
            clean_status,
        )

        return self.create_notification(
            user_id=user_id,
            message=message,
        )

    def get_notifications(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Notification]:

        return (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def mark_as_read(
        self,
        notification_id: int,
        user_id: str,
    ) -> Notification | None:
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
