"""
NotificationService — persistence + real-time push for all in-app notifications.

Design decisions:
  - Every notification is persisted to the DB so users can retrieve history
    after reconnecting (REST /notifications/).
  - After saving, the notification is immediately pushed over WebSocket to the
    user's personal notification channel (notifications_{user_id}).
  - The WebSocket push is deferred via on_commit (inside broadcast_to_user),
    so the push only fires if the surrounding DB transaction succeeds.
  - Notification creation is always wrapped in try/except at the call-sites
    in OrderService and ChatService: a notification failure must never break
    the primary business operation.

Notification types (see models.NotificationType):
  NEW_ORDER        — vendor receives when a customer places an order
  ORDER_STATUS     — customer (+ optionally rider/vendor) receives on status change
  RIDER_ASSIGNED   — customer + rider receive when admin assigns a rider
  CHAT_MESSAGE     — recipient(s) receive when a new chat message arrives
  SYSTEM           — admin-generated system alerts
"""

import logging

from django.utils import timezone

from core.channel_utils import broadcast_to_user

from .models import Notification, NotificationType
from .serializers import NotificationSerializer

logger = logging.getLogger(__name__)


class NotificationService:

    # ──────────────────────────────────────────
    # Creation
    # ──────────────────────────────────────────

    @staticmethod
    def create(recipient, notification_type: str, title: str, message: str, data: dict = None) -> Notification:
        """
        Persist a notification and push it to the recipient's WebSocket channel.
        Must be called inside an active DB transaction so that on_commit fires
        only after the surrounding operation commits.

        Args:
            recipient:          User instance who should receive this notification.
            notification_type:  One of NotificationType choices.
            title:              Short summary (used as push notification title).
            message:            Human-readable detail.
            data:               Arbitrary JSON payload for the frontend.
        """
        notif = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {},
        )

        # Push over WebSocket — deferred until the enclosing transaction commits.
        broadcast_to_user(
            user_id=recipient.pk,
            message={
                "type": "notification.push",
                "data": {
                    "type": "NOTIFICATION_PUSH",
                    "notification": NotificationSerializer(notif).data,
                },
            },
        )

        logger.info(
            "Notification created: type=%s recipient=%s title='%s'",
            notification_type,
            recipient.email,
            title,
        )
        return notif

    @staticmethod
    def notify_many(recipients, notification_type: str, title: str, message: str, data: dict = None) -> list:
        """
        Create notifications for multiple recipients efficiently.
        Each recipient gets their own WebSocket push.
        """
        notifications = []
        for recipient in recipients:
            try:
                notif = NotificationService.create(
                    recipient=recipient,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    data=data,
                )
                notifications.append(notif)
            except Exception as exc:
                logger.error(
                    "Failed to notify %s (type=%s): %s", recipient.email, notification_type, exc
                )
        return notifications

    # ──────────────────────────────────────────
    # Read management (REST layer)
    # ──────────────────────────────────────────

    @staticmethod
    def mark_read(notification_id, user) -> bool:
        """
        Mark a single notification as read.
        Returns True if the notification was found and updated, False otherwise.
        """
        updated = Notification.objects.filter(
            pk=notification_id,
            recipient=user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        return updated > 0

    @staticmethod
    def mark_all_read(user) -> int:
        """Mark all unread notifications for a user as read. Returns count."""
        return Notification.objects.filter(
            recipient=user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())

    @staticmethod
    def get_unread_count(user) -> int:
        return Notification.objects.filter(recipient=user, is_read=False).count()

    @staticmethod
    def get_for_user(user, is_read: bool = None):
        """
        Return all notifications for a user, optionally filtered by read status.
        Ordered newest-first (set by model Meta).
        """
        qs = Notification.objects.filter(recipient=user)
        if is_read is not None:
            qs = qs.filter(is_read=is_read)
        return qs
