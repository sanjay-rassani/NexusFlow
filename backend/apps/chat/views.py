"""
Chat REST endpoints — history access and room management.

WebSocket (ws/chat/<room_id>/) handles real-time messaging.
REST handles:
  - Listing rooms the user belongs to
  - Fetching full room detail + recent messages
  - Cursor-paginated message history (older messages)
  - Marking all messages in a room as read
  - Creating/joining a room (lazy — triggered by order context)

Endpoints:
  GET  /api/v1/chat/rooms/                 — list my rooms
  GET  /api/v1/chat/rooms/{id}/            — room detail + 50 recent msgs
  GET  /api/v1/chat/rooms/{id}/messages/   — cursor-paginated history
  POST /api/v1/chat/rooms/{id}/messages/   — send a message via REST
  POST /api/v1/chat/rooms/{id}/read/       — mark all messages read
  POST /api/v1/chat/orders/{order_id}/room/ — get-or-create room for an order
"""

import logging

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatRoom
from .serializers import (
    ChatRoomDetailSerializer,
    ChatRoomSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)
from .services import ChatService

logger = logging.getLogger(__name__)


class ChatRoomListView(generics.ListAPIView):
    """
    GET /api/v1/chat/rooms/
    Returns all chat rooms the authenticated user participates in.
    """

    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatService.get_rooms_for_user(self.request.user)


class ChatRoomDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/chat/rooms/{id}/
    Room detail with the 50 most recent messages.
    """

    serializer_class = ChatRoomDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return ChatService.get_room_for_user(
            room_id=self.kwargs["pk"],
            user=self.request.user,
        )


class ChatMessageListView(generics.ListAPIView):
    """
    GET /api/v1/chat/rooms/{room_id}/messages/?before=<message_uuid>
    Cursor-paginated message history.
    Supports loading earlier messages (infinite scroll upward).
    """

    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        room = ChatService.get_room_for_user(
            room_id=self.kwargs["room_id"],
            user=self.request.user,
        )
        before_id = self.request.query_params.get("before")
        return ChatService.get_message_history(room=room, limit=50, before_id=before_id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "results": serializer.data,
            "has_more": len(queryset) == 50,
        })


class ChatMessageSendView(APIView):
    """
    POST /api/v1/chat/rooms/{room_id}/messages/
    REST fallback for sending a message (WebSocket preferred for real-time UX).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, room_id):
        room = ChatService.get_room_for_user(room_id=room_id, user=request.user)
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        msg = ChatService.send_message(
            room=room,
            sender=request.user,
            content=serializer.validated_data["content"],
        )
        return Response(
            MessageSerializer(msg, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ChatRoomMarkReadView(APIView):
    """
    POST /api/v1/chat/rooms/{room_id}/read/
    Mark all unread messages (not sent by self) in the room as read.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, room_id):
        room = ChatService.get_room_for_user(room_id=room_id, user=request.user)
        count = ChatService.mark_room_read(room=room, user=request.user)
        return Response({"marked_count": count})


class ChatRoomGetOrCreateView(APIView):
    """
    POST /api/v1/chat/orders/{order_id}/room/
    Lazily creates (or fetches) the chat room for an order.
    Only the order's customer, vendor owner, and assigned rider may access.
    Returns the room detail.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        from apps.orders.models import Order

        try:
            order = Order.objects.select_related("vendor__owner", "customer").get(pk=order_id)
        except Order.DoesNotExist:
            return Response(
                {"error": True, "code": "ORDER_NOT_FOUND", "message": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = request.user
        is_customer = order.customer == user
        is_vendor_owner = (
            hasattr(order.vendor, "owner") and order.vendor.owner == user
        )
        is_rider = (
            order.rider_id is not None and str(order.rider_id) == str(user.pk)
        )

        if not (is_customer or is_vendor_owner or is_rider or user.is_staff):
            return Response(
                {"error": True, "code": "FORBIDDEN", "message": "Access denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        room = ChatService.get_or_create_room(order)

        # Ensure current user is a participant (covers edge cases like late rider join)
        ChatService.add_participant(room, user)

        serializer = ChatRoomDetailSerializer(room, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
