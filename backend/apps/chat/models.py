"""
Chat models — real-time messaging between roles.
Full consumer implementation in Phase 8.
"""

import uuid

from django.conf import settings
from django.db import models


class ChatRoom(models.Model):
    """
    A chat room scoped to an order (customer ↔ vendor ↔ rider).
    Naming: order_{order_id}
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="chat_room",
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="chat_rooms",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_rooms"

    def __str__(self):
        return f"Chat for Order {self.order.id}"

    @property
    def room_name(self):
        return f"order_{self.order.id}"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["room", "created_at"]),
            models.Index(fields=["sender"]),
        ]

    def __str__(self):
        return f"Message from {self.sender.email} in {self.room}"
