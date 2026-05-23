"""
Chat URL patterns — mounted under /api/v1/chat/ in config/urls.py.
"""

from django.urls import path

from .views import (
    ChatMessageListView,
    ChatMessageSendView,
    ChatRoomDetailView,
    ChatRoomGetOrCreateView,
    ChatRoomListView,
    ChatRoomMarkReadView,
)

urlpatterns = [
    # Room listing
    path("rooms/", ChatRoomListView.as_view(), name="chat-room-list"),

    # Room detail (+ 50 recent messages)
    path("rooms/<uuid:pk>/", ChatRoomDetailView.as_view(), name="chat-room-detail"),

    # Paginated message history + REST send
    path("rooms/<uuid:room_id>/messages/", ChatMessageListView.as_view(), name="chat-message-list"),
    path("rooms/<uuid:room_id>/messages/send/", ChatMessageSendView.as_view(), name="chat-message-send"),

    # Mark messages read
    path("rooms/<uuid:room_id>/read/", ChatRoomMarkReadView.as_view(), name="chat-room-read"),

    # Get or create room for an order
    path("orders/<uuid:order_id>/room/", ChatRoomGetOrCreateView.as_view(), name="chat-order-room"),
]
