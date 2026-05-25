"""
Channel layer broadcast utilities.

Key design: broadcast() defers the actual send until AFTER the current
database transaction commits via django.db.transaction.on_commit().

Why this matters:
  Services call broadcast() inside @transaction.atomic blocks.
  If we sent the WebSocket event immediately and the transaction later
  rolled back, clients would receive a phantom update for a DB state
  that never persisted. on_commit() guarantees events only fire on success.

Usage:
    broadcast(
        group="order_<uuid>",
        message={"type": "order.status.updated", "data": {...}},
    )

The "type" key in the message maps to the consumer method:
    "order.status.updated"  →  order_status_updated(self, event)
    "rider.location.updated" → rider_location_updated(self, event)
    "notification.push"      → notification_push(self, event)
"""

import logging

from asgiref.sync import async_to_sync
from django.db import transaction

logger = logging.getLogger(__name__)


def get_layer():
    """Return the configured channel layer, or None if not available."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


def broadcast(group: str, message: dict, use_on_commit: bool = True) -> None:
    """
    Send a message to a channel group.

    Args:
        group:          Channel group name (e.g. "order_<uuid>").
        message:        Dict with at least a "type" key (dot-separated, maps
                        to underscore-named consumer method).
        use_on_commit:  If True (default), defers send until the active
                        transaction commits. Set False only if called outside
                        a transaction context.
    """
    layer = get_layer()
    if not layer:
        logger.warning("Channel layer not configured — skipping broadcast to '%s'.", group)
        return

    def _send():
        try:
            async_to_sync(layer.group_send)(group, message)
            logger.debug("Broadcast to group '%s': type=%s", group, message.get("type"))
        except Exception as exc:
            logger.error(
                "Failed to broadcast to group '%s': %s", group, exc, exc_info=True
            )

    if use_on_commit:
        transaction.on_commit(_send)
    else:
        _send()


def broadcast_to_user(user_id, message: dict) -> None:
    """
    Send a message to a specific user's personal notification channel.
    Group name format: notifications_{user_id}
    """
    broadcast(group=f"notifications_{user_id}", message=message)


def broadcast_to_order(order_id, message: dict) -> None:
    """Send to all subscribers of an order's status channel."""
    broadcast(group=f"order_{order_id}", message=message)


def broadcast_rider_location(rider_id, message: dict) -> None:
    """Send to all subscribers watching a rider's live location."""
    broadcast(group=f"rider_location_{rider_id}", message=message, use_on_commit=False)


def broadcast_to_chat_room(room_id, message: dict, use_on_commit: bool = True) -> None:
    """
    Send a message to all participants connected to a chat room.
    Group name format: chat_room_{room_id}

    use_on_commit=True when called inside a DB transaction (send_message).
    use_on_commit=False for ephemeral events like typing indicators that have
    no DB write behind them.
    """
    broadcast(group=f"chat_room_{room_id}", message=message, use_on_commit=use_on_commit)
