"""
RiderLocationConsumer — WebSocket endpoint for live GPS tracking.

Channel group: rider_location_{rider_id}
URL:           ws/rider/{rider_id}/location/

Two roles on this single endpoint:

  SENDER (the rider):
    Connects to their own channel (rider_id == their user pk).
    Sends JSON: {"type": "location_update", "lat": 24.86, "lng": 67.00}
    Consumer validates they are the rider, saves to DB, broadcasts to group.

  RECEIVER (customer / admin):
    Connects to watch a specific rider.
    Only allowed if the user has an active delivery assigned to this rider
    (or is an admin).
    Receives: {"type": "RIDER_LOCATION_UPDATED", "rider_id": "...", "lat": ..., "lng": ...}

On connect:
  Sends last known location immediately so the map renders without waiting.
"""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class RiderLocationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.rider_id = self.scope["url_route"]["kwargs"]["rider_id"]
        self.group_name = f"rider_location_{self.rider_id}"

        has_access = await self._can_access(user, self.rider_id)
        if not has_access:
            logger.warning(
                "WS rejected: user %s cannot access rider %s location.",
                user.email,
                self.rider_id,
            )
            await self.close(code=4003)
            return

        # Track whether this connection is the rider themselves (sender mode)
        self.is_rider = str(user.pk) == str(self.rider_id)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info(
            "WS connected: user=%s rider_id=%s mode=%s",
            user.email,
            self.rider_id,
            "sender" if self.is_rider else "receiver",
        )

        # Push last known location immediately
        last_location = await self._get_last_location(self.rider_id)
        if last_location:
            await self.send(text_data=json.dumps({
                "type": "RIDER_LOCATION_UPDATED",
                "rider_id": str(self.rider_id),
                "lat": float(last_location["lat"]),
                "lng": float(last_location["lng"]),
            }))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # ──────────────────────────────────────────
    # Receive from client (only rider sends location)
    # ──────────────────────────────────────────

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return

        msg_type = data.get("type")

        if msg_type == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
            return

        if msg_type == "location_update" and self.is_rider:
            lat = data.get("lat")
            lng = data.get("lng")

            if lat is None or lng is None:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "lat and lng are required.",
                }))
                return

            # Persist + broadcast (DB write in thread pool)
            await self._save_and_broadcast(self.rider_id, lat, lng)

    # ──────────────────────────────────────────
    # Handler for channel layer messages
    # ──────────────────────────────────────────

    async def rider_location_updated(self, event):
        """Receives broadcast from _save_and_broadcast and forwards to client."""
        await self.send(text_data=json.dumps(event["data"]))

    # ──────────────────────────────────────────
    # DB helpers
    # ──────────────────────────────────────────

    @database_sync_to_async
    def _can_access(self, user, rider_id):
        """
        True if the user is:
          - The rider themselves
          - An admin
          - A customer with an active delivery assigned to this rider
        """
        from apps.users.models import UserRole
        from apps.orders.models import Order, OrderStatus

        if user.role == UserRole.ADMIN:
            return True
        if str(user.pk) == str(rider_id):
            return True
        if user.role == UserRole.CUSTOMER:
            active_statuses = [
                OrderStatus.PICKED_UP,
                OrderStatus.ON_THE_WAY,
                OrderStatus.READY_FOR_PICKUP,
            ]
            return Order.objects.filter(
                customer=user,
                rider_id=rider_id,
                status__in=active_statuses,
            ).exists()
        return False

    @database_sync_to_async
    def _get_last_location(self, rider_id):
        """Returns the rider's most recent GPS coordinates, or None."""
        from apps.delivery.models import RiderProfile

        try:
            profile = RiderProfile.objects.get(rider_id=rider_id)
            if profile.current_lat is not None and profile.current_lng is not None:
                return {"lat": profile.current_lat, "lng": profile.current_lng}
        except RiderProfile.DoesNotExist:
            pass
        return None

    @database_sync_to_async
    def _save_and_broadcast(self, rider_id, lat: float, lng: float):
        """
        Saves GPS coordinates to DB and broadcasts to the group.
        DB write happens in thread pool; channel_layer.group_send is sync here.
        """
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        from apps.delivery.models import RiderLocationHistory, RiderProfile
        from apps.users.models import User

        try:
            rider = User.objects.get(pk=rider_id)
        except User.DoesNotExist:
            return

        # Update current position on profile
        RiderProfile.objects.filter(rider=rider).update(
            current_lat=lat,
            current_lng=lng,
        )

        # Append to history
        RiderLocationHistory.objects.create(rider=rider, lat=lat, lng=lng)

        # Broadcast to group (sync call inside sync context)
        layer = get_channel_layer()
        if layer:
            payload = {
                "type": "rider.location.updated",
                "data": {
                    "type": "RIDER_LOCATION_UPDATED",
                    "rider_id": str(rider_id),
                    "lat": lat,
                    "lng": lng,
                },
            }
            async_to_sync(layer.group_send)(self.group_name, payload)

        logger.debug("Location saved and broadcast: rider=%s lat=%s lng=%s", rider_id, lat, lng)
