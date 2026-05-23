"""
WebSocket URL routing.
Each app contributes its own WebSocket URL patterns here.
Populated in Phase 5 (WebSocket integration).
"""

from django.urls import path

# Placeholder — consumers will be registered here in Phase 5
websocket_urlpatterns = [
    # Example (added in Phase 5):
    # path("ws/orders/<int:order_id>/", consumers.OrderConsumer.as_asgi()),
    # path("ws/notifications/", consumers.NotificationConsumer.as_asgi()),
    # path("ws/chat/<str:room_name>/", consumers.ChatConsumer.as_asgi()),
    # path("ws/rider/<int:rider_id>/location/", consumers.RiderLocationConsumer.as_asgi()),
]
