"""
ChatConsumer — real-time messaging WebSocket for a single chat room.

URL:   ws/chat/<room_id>/?token=<jwt>
Group: chat_room_{room_id}

Access: Only authenticated users who are participants in the room may connect.
        Non-participants are rejected with close code 4003.

Client → Server messages:
  {"type": "ping"}
  {"type": "message",   "content": "Hello!"}
  {"type": "typing"}
  {"type": "stop_typing"}
  {"type": "mark_read"}

Server → Client messages:
  {"type": "pong"}
  {"type": "CHAT_MESSAGE",    "room_id": "...", "message": {...}}
  {"type": "CHAT_TYPING",     "room_id": "...", "user_id": "...", "user_name": "..."}
  {"type": "CHAT_STOP_TYPING","room_id": "...", "user_id": "..."}
  {"type": "CHAT_READ",       "room_id": "...", "user_id": "...", "timestamp": "..."}
  {"type": "CHAT_HISTORY",    "messages": [...], "has_more": bool}

Channel-layer → Consumer handlers (dot → underscore):
  "chat.message"    → chat_message()
  "chat.typing"     → chat_typing()
  "chat.stop_typing"→ chat_stop_typing()
  "chat.read"       → chat_read()
"""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

# Maximum content length accepted per message (characters)
MAX_MESSAGE_LENGTH = 4096


class ChatConsumer(AsyncWebsocketConsumer):

    # ──────────────────────────────────────────
    # Connection lifecycle
    # ──────────────────────────────────────────

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.user = user
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]

        # Validate room and participant access
        room = await self._get_room_if_participant(str(self.room_id))
        if room is None:
            logger.warning(
                "Chat WS: user %s is not a participant in room %s", user.email, self.room_id
            )
            await self.close(code=4003)
            return

        self.room = room
        self.group_name = f"chat_room_{self.room_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info(
            "Chat WS connected: user=%s room=%s", user.email, self.room_id
        )

        # Deliver the 50 most recent messages immediately on connect
        history = await self._get_recent_history()
        await self.send(text_data=json.dumps({
            "type": "CHAT_HISTORY",
            "room_id": str(self.room_id),
            "messages": history,
            "has_more": len(history) == 50,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(
            "Chat WS disconnected: user=%s room=%s code=%s",
            getattr(self, "user", {}).email if hasattr(self, "user") else "?",
            getattr(self, "room_id", "?"),
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

        elif msg_type == "message":
            content = (data.get("content") or "").strip()
            if not content:
                return
            if len(content) > MAX_MESSAGE_LENGTH:
                await self.send(text_data=json.dumps({
                    "type": "ERROR",
                    "code": "MESSAGE_TOO_LONG",
                    "message": f"Message exceeds {MAX_MESSAGE_LENGTH} characters.",
                }))
                return
            await self._handle_send_message(content)

        elif msg_type == "typing":
            await self._broadcast_typing(typing=True)

        elif msg_type == "stop_typing":
            await self._broadcast_typing(typing=False)

        elif msg_type == "mark_read":
            count = await self._mark_room_read()
            await self.send(text_data=json.dumps({
                "type": "MARK_READ_ACK",
                "room_id": str(self.room_id),
                "marked_count": count,
            }))

    # ──────────────────────────────────────────
    # Channel-layer event handlers
    # ──────────────────────────────────────────

    async def chat_message(self, event):
        """Broadcast persisted message to this WebSocket connection."""
        await self.send(text_data=json.dumps(event["data"]))

    async def chat_typing(self, event):
        """Forward typing indicator — skip echoing back to the sender."""
        if event["data"].get("user_id") != str(self.user.pk):
            await self.send(text_data=json.dumps(event["data"]))

    async def chat_stop_typing(self, event):
        """Forward stop-typing indicator — skip echoing back to the sender."""
        if event["data"].get("user_id") != str(self.user.pk):
            await self.send(text_data=json.dumps(event["data"]))

    async def chat_read(self, event):
        """Forward read receipt to all participants."""
        await self.send(text_data=json.dumps(event["data"]))

    # ──────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────

    async def _handle_send_message(self, content: str):
        """Persist the message via the service layer (runs DB write in thread)."""
        await self._save_and_broadcast(content)

    async def _broadcast_typing(self, typing: bool):
        """Immediately send a typing indicator — no DB write, no on_commit."""
        from asgiref.sync import sync_to_async
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        event_type = "chat.typing" if typing else "chat.stop_typing"
        client_type = "CHAT_TYPING" if typing else "CHAT_STOP_TYPING"

        layer = self.channel_layer
        await layer.group_send(
            self.group_name,
            {
                "type": event_type,
                "data": {
                    "type": client_type,
                    "room_id": str(self.room_id),
                    "user_id": str(self.user.pk),
                    "user_name": self.user.get_full_name() or self.user.email,
                },
            },
        )

    # ──────────────────────────────────────────
    # DB helpers (run in sync thread pool)
    # ──────────────────────────────────────────

    @database_sync_to_async
    def _get_room_if_participant(self, room_id: str):
        """Return the ChatRoom if user is a participant, else None."""
        from apps.chat.models import ChatRoom
        try:
            room = ChatRoom.objects.get(pk=room_id)
            if room.participants.filter(pk=self.user.pk).exists():
                return room
            return None
        except (ChatRoom.DoesNotExist, Exception):
            return None

    @database_sync_to_async
    def _save_and_broadcast(self, content: str):
        from apps.chat.services import ChatService
        ChatService.send_message(room=self.room, sender=self.user, content=content)

    @database_sync_to_async
    def _mark_room_read(self) -> int:
        from apps.chat.services import ChatService
        return ChatService.mark_room_read(room=self.room, user=self.user)

    @database_sync_to_async
    def _get_recent_history(self) -> list:
        from apps.chat.models import Message
        messages = (
            Message.objects
            .filter(room=self.room)
            .select_related("sender")
            .order_by("-created_at")[:50]
        )
        return [
            {
                "id": str(m.id),
                "sender_id": str(m.sender.pk),
                "sender_email": m.sender.email,
                "sender_name": m.sender.get_full_name() or m.sender.email,
                "content": m.content,
                "is_read": m.is_read,
                "read_at": m.read_at.isoformat() if m.read_at else None,
                "created_at": m.created_at.isoformat(),
                "is_own": m.sender_id == self.user.pk,
            }
            for m in reversed(list(messages))
        ]
