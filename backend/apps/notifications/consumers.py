"""
NotificationConsumer — per-user personal notification WebSocket.

Channel group: notifications_{user_pk}
URL:           ws/notifications/

Every authenticated user connects here to receive real-time push events:
  - New order notifications (vendor)
  - Order status updates (customer)
  - Rider assignment (customer)
  - Chat messages (all roles) — Phase 8
  - System alerts (admin)

The REST layer (OrderService, ChatService, etc.) pushes to this group
using core.channel_utils.broadcast_to_user(user_id, message).

Incoming messages (client → server):
  {"type": "ping"}
  {"type": "mark_read", "notification_id": "..."}   — marks DB notification read

Outgoing messages (server → client):
  {"type": "notification.push", "data": {...}}
"""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.user = user
        self.group_name = f"notifications_{user.pk}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info("Notification WS connected: user=%s", user.email)

        # Send unread notification count immediately on connect
        unread_count = await self._get_unread_count(user)
        await self.send(text_data=json.dumps({
            "type": "UNREAD_COUNT",
            "count": unread_count,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(
            "Notification WS disconnected: user=%s code=%s",
            getattr(self, "user", {}).email if hasattr(self, "user") else "?",
            close_code,
        )

    # ──────────────────────────────────────────
    # Receive from client
    # ──────────────────────────────────────────

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return

        msg_type = data.get("type")

        if msg_type == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))

        elif msg_type == "mark_read":
            notification_id = data.get("notification_id")
            if notification_id:
                success = await self._mark_notification_read(self.user, notification_id)
                await self.send(text_data=json.dumps({
                    "type": "MARK_READ_ACK",
                    "notification_id": notification_id,
                    "success": success,
                }))

        elif msg_type == "mark_all_read":
            count = await self._mark_all_read(self.user)
            await self.send(text_data=json.dumps({
                "type": "MARK_ALL_READ_ACK",
                "marked_count": count,
            }))

    # ──────────────────────────────────────────
    # Handler for channel layer messages
    # ──────────────────────────────────────────

    async def notification_push(self, event):
        """
        Called when core.channel_utils.broadcast_to_user() sends a message.
        Forwards the payload directly to the WebSocket client.
        """
        await self.send(text_data=json.dumps(event["data"]))

    # ──────────────────────────────────────────
    # DB helpers
    # ──────────────────────────────────────────

    @database_sync_to_async
    def _get_unread_count(self, user):
        from apps.notifications.models import Notification
        return Notification.objects.filter(recipient=user, is_read=False).count()

    @database_sync_to_async
    def _mark_notification_read(self, user, notification_id: str) -> bool:
        from django.utils import timezone
        from apps.notifications.models import Notification

        updated = Notification.objects.filter(
            pk=notification_id, recipient=user, is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return updated > 0

    @database_sync_to_async
    def _mark_all_read(self, user) -> int:
        from django.utils import timezone
        from apps.notifications.models import Notification

        return Notification.objects.filter(
            recipient=user, is_read=False
        ).update(is_read=True, read_at=timezone.now())
