"""
OrderStatusConsumer — WebSocket endpoint for live order tracking.

Channel group: order_{order_id}
URL:           ws/orders/{order_id}/

Who can connect:
  - The customer who placed the order
  - The vendor who owns the order
  - The assigned rider
  - Any admin user

On connect:
  1. JWT middleware has already set scope["user"]
  2. Consumer validates auth and order access
  3. Joins the channel group
  4. Sends the current order state immediately (so UI syncs on reconnect)

Incoming messages (client → server):
  {"type": "ping"}                → server replies {"type": "pong"}

Outgoing messages (server → client):
  {"type": "ORDER_STATUS_UPDATED", "order_id": "...", "status": "..."}
  {"type": "RIDER_ASSIGNED",       "order_id": "...", "rider": {...}}
  {"type": "NEW_ORDER",            "order_id": "...", ...}
  {"type": "pong"}
"""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class OrderStatusConsumer(AsyncWebsocketConsumer):

    # ──────────────────────────────────────────
    # Connection lifecycle
    # ──────────────────────────────────────────

    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            logger.warning("WS rejected: unauthenticated connection to OrderStatusConsumer.")
            await self.close(code=4001)
            return

        self.order_id = self.scope["url_route"]["kwargs"]["order_id"]
        self.group_name = f"order_{self.order_id}"

        # Validate the user has permission to track this order
        order = await self._get_accessible_order(user, self.order_id)
        if order is None:
            logger.warning(
                "WS rejected: user %s has no access to order %s.",
                user.email,
                self.order_id,
            )
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info(
            "WS connected: user=%s order=%s group=%s",
            user.email,
            self.order_id,
            self.group_name,
        )

        # Push current state immediately on connect so client is always in sync
        await self.send(text_data=json.dumps({
            "type": "ORDER_STATUS",
            "order_id": str(self.order_id),
            "status": order.status,
            "vendor_name": order.vendor.name,
            "rider_email": order.rider.email if order.rider else None,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info("WS disconnected: order=%s code=%s", getattr(self, "order_id", "?"), close_code)

    # ──────────────────────────────────────────
    # Receive from client
    # ──────────────────────────────────────────

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return

        if data.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))

    # ──────────────────────────────────────────
    # Handlers for channel layer messages
    # (method names mirror "type" with dots → underscores)
    # ──────────────────────────────────────────

    async def order_status_updated(self, event):
        """Triggered by OrderService._emit_event("ORDER_STATUS_UPDATED", ...)"""
        await self.send(text_data=json.dumps(event["data"]))

    async def new_order(self, event):
        """Triggered when a new order is placed (for vendor-side consumers)."""
        await self.send(text_data=json.dumps(event["data"]))

    async def rider_assigned(self, event):
        """Triggered when admin assigns a rider."""
        await self.send(text_data=json.dumps(event["data"]))

    # ──────────────────────────────────────────
    # DB helpers (run in thread pool)
    # ──────────────────────────────────────────

    @database_sync_to_async
    def _get_accessible_order(self, user, order_id):
        """
        Returns the order if the user is the customer, vendor owner,
        assigned rider, or admin. Returns None otherwise.
        """
        from apps.orders.models import Order
        from apps.users.models import UserRole

        try:
            order = (
                Order.objects
                .select_related("customer", "vendor__owner", "rider")
                .get(pk=order_id)
            )
        except (Order.DoesNotExist, Exception):
            return None

        role = user.role
        if role == UserRole.ADMIN:
            return order
        if role == UserRole.CUSTOMER and order.customer == user:
            return order
        if role == UserRole.VENDOR and order.vendor.owner == user:
            return order
        if role == UserRole.RIDER and order.rider == user:
            return order

        return None
