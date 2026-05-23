"""
Notification model.
Full WebSocket delivery and Celery email tasks implemented in Phase 9.
"""

import uuid

from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    ORDER_STATUS = "ORDER_STATUS", "Order Status Update"
    NEW_ORDER = "NEW_ORDER", "New Order"
    RIDER_ASSIGNED = "RIDER_ASSIGNED", "Rider Assigned"
    CHAT_MESSAGE = "CHAT_MESSAGE", "New Chat Message"
    SYSTEM = "SYSTEM", "System Alert"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)  # Arbitrary payload for frontend
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["recipient", "created_at"]),
        ]

    def __str__(self):
        return f"{self.notification_type} → {self.recipient.email}"
