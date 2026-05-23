"""
Delivery service layer.

RiderLocationService handles the REST fallback path for location updates —
the primary path is via WebSocket (RiderLocationConsumer), but mobile clients
that need a REST fallback can POST to /api/v1/delivery/location/.
Both paths use this service to persist and broadcast.
"""

import logging

from .models import RiderLocationHistory, RiderProfile

logger = logging.getLogger(__name__)


class RiderLocationService:

    @staticmethod
    def update_location(rider, lat: float, lng: float) -> None:
        """
        Persists the rider's current GPS position and broadcasts to watchers.

        Called from:
          - RiderLocationConsumer (WebSocket receive) — already async, DB write in thread pool
          - DeliveryLocationUpdateView (REST fallback) — sync Django view
        """
        from core.channel_utils import broadcast_rider_location

        # Update current position snapshot on the profile
        RiderProfile.objects.filter(rider=rider).update(
            current_lat=lat,
            current_lng=lng,
        )

        # Append to location history
        RiderLocationHistory.objects.create(rider=rider, lat=lat, lng=lng)

        # Broadcast to all WebSocket subscribers of this rider's location channel
        broadcast_rider_location(
            rider_id=rider.pk,
            message={
                "type": "rider.location.updated",
                "data": {
                    "type": "RIDER_LOCATION_UPDATED",
                    "rider_id": str(rider.pk),
                    "lat": lat,
                    "lng": lng,
                },
            },
        )

        logger.debug("Location updated: rider=%s lat=%s lng=%s", rider.email, lat, lng)
