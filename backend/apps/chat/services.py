"""
ChatService — all business logic for the chat system.

Design decisions:
  - Chat rooms are scoped to an Order (one room per order).
  - Participants are added lazily: customer + vendor when the room is first
    accessed, rider when they are assigned to the order.
  - Messages are broadcast over WebSocket AND saved to the database so that
    history is available when a participant reconnects.
  - Typing indicators and read receipts are ephemeral WebSocket events —
    they are NOT persisted to the database.
"""

import logging
from typing import Optional

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers as drf_serializers

from core.channel_utils import broadcast_to_chat_room

from .models import ChatRoom, Message

logger = logging.getLogger(__name__)


class ChatService:

    # ──────────────────────────────────────────
    # Room management
    # ──────────────────────────────────────────

    @staticmethod
    def get_or_create_room(order) -> ChatRoom:
        """
        Return the existing chat room for an order, or create one.
        Initial participants: customer (order owner) + vendor owner.
        Called on first WebSocket connect or REST room-detail request.
        """
        try:
            return order.chat_room
        except ChatRoom.DoesNotExist:
            pass

        with transaction.atomic():
            room, created = ChatRoom.objects.get_or_create(order=order)
            if created:
                participants = [order.customer]
                if hasattr(order.vendor, "owner") and order.vendor.owner:
                    participants.append(order.vendor.owner)
                room.participants.set(participants)
                logger.info(
                    "Chat room created for order %s (participants: %s)",
                    order.id,
                    [u.email for u in participants],
                )
        return room

    @staticmethod
    def add_participant(room: ChatRoom, user) -> None:
        """
        Add a user to a chat room if they are not already a participant.
        Called when a rider is assigned to an order.
        """
        if not room.participants.filter(pk=user.pk).exists():
            room.participants.add(user)
            logger.info("Added participant %s to chat room %s", user.email, room.id)

    @staticmethod
    def get_room_for_user(room_id, user) -> ChatRoom:
        """
        Fetch a room by PK and verify the user is a participant.
        Raises ValidationError if not found or not a participant.
        """
        try:
            room = ChatRoom.objects.prefetch_related("participants", "messages").get(pk=room_id)
        except ChatRoom.DoesNotExist:
            raise drf_serializers.ValidationError({"detail": "Chat room not found."})

        if not room.participants.filter(pk=user.pk).exists():
            raise drf_serializers.ValidationError(
                {"detail": "You are not a participant in this chat room."}
            )
        return room

    @staticmethod
    def get_rooms_for_user(user):
        """Return all chat rooms the user participates in, newest first."""
        return (
            ChatRoom.objects.filter(participants=user)
            .prefetch_related("participants", "messages")
            .select_related("order")
            .order_by("-created_at")
        )

    # ──────────────────────────────────────────
    # Messaging
    # ──────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def send_message(room: ChatRoom, sender, content: str) -> Message:
        """
        Persist a message and broadcast it to the chat room WebSocket group.
        Broadcast is deferred via on_commit so it only fires if the DB write succeeds.

        Returns the saved Message instance.
        """
        if not room.participants.filter(pk=sender.pk).exists():
            raise drf_serializers.ValidationError(
                {"detail": "Sender is not a participant in this room."}
            )

        msg = Message.objects.create(room=room, sender=sender, content=content)
        logger.info(
            "Message saved: room=%s sender=%s length=%d", room.id, sender.email, len(content)
        )

        # Build the WebSocket payload now (inside the transaction) so serialization
        # errors surface before on_commit.
        payload = {
            "type": "chat.message",
            "data": {
                "type": "CHAT_MESSAGE",
                "room_id": str(room.id),
                "message": {
                    "id": str(msg.id),
                    "sender_id": str(sender.pk),
                    "sender_email": sender.email,
                    "sender_name": sender.get_full_name() or sender.email,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "is_read": False,
                },
            },
        }
        broadcast_to_chat_room(room.id, payload, use_on_commit=True)
        return msg

    @staticmethod
    def mark_room_read(room: ChatRoom, user) -> int:
        """
        Mark all unread messages (not sent by this user) as read.
        Returns the count of messages marked.
        """
        updated = Message.objects.filter(
            room=room,
            is_read=False,
        ).exclude(sender=user).update(is_read=True, read_at=timezone.now())

        if updated:
            broadcast_to_chat_room(
                room.id,
                {
                    "type": "chat.read",
                    "data": {
                        "type": "CHAT_READ",
                        "room_id": str(room.id),
                        "user_id": str(user.pk),
                        "user_email": user.email,
                        "timestamp": timezone.now().isoformat(),
                    },
                },
                use_on_commit=False,
            )
            logger.info(
                "Marked %d messages read in room %s by %s", updated, room.id, user.email
            )
        return updated

    @staticmethod
    def get_message_history(room: ChatRoom, limit: int = 50, before_id: Optional[str] = None):
        """
        Return paginated message history for a room (cursor-based).
        before_id: UUID of the oldest message the client already has.
                   If provided, returns messages older than that message.
        """
        qs = Message.objects.filter(room=room).select_related("sender").order_by("-created_at")
        if before_id:
            try:
                anchor = Message.objects.get(pk=before_id, room=room)
                qs = qs.filter(created_at__lt=anchor.created_at)
            except Message.DoesNotExist:
                pass
        return list(reversed(list(qs[:limit])))
