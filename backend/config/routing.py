"""
WebSocket URL routing — all consumers registered here.

Pattern → Consumer mapping:
  ws/orders/{order_id}/          → OrderStatusConsumer
  ws/rider/{rider_id}/location/  → RiderLocationConsumer
  ws/notifications/              → NotificationConsumer

Auth: All connections go through JWTAuthMiddlewareStack (configured in asgi.py).
      Consumers close the connection (code 4001) if the user is not authenticated.

UUID note: order_id uses the full UUID string pattern; rider_id is UUID too
since User.pk is a UUID field.
"""

from django.urls import path

from apps.delivery.consumers import RiderLocationConsumer
from apps.notifications.consumers import NotificationConsumer
from apps.orders.consumers import OrderStatusConsumer

websocket_urlpatterns = [
    # Order status tracking
    # Client: ws://host/ws/orders/<uuid>/?token=<jwt>
    path("ws/orders/<uuid:order_id>/", OrderStatusConsumer.as_asgi()),

    # Rider live location
    # Rider sends:    ws://host/ws/rider/<uuid>>/location/?token=<jwt>
    # Customer views: same URL (receives broadcasts)
    path("ws/rider/<uuid:rider_id>/location/", RiderLocationConsumer.as_asgi()),

    # Per-user notification stream
    # Client: ws://host/ws/notifications/?token=<jwt>
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]
