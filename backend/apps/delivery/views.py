"""
Delivery views.
Primary real-time path: WebSocket (RiderLocationConsumer).
REST path: fallback for clients that can't maintain a WebSocket connection.
"""

from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsRider

from .services import RiderLocationService


class LocationUpdateSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)


class RiderLocationUpdateView(APIView):
    """
    POST /api/v1/delivery/location/
    REST fallback for riders to push GPS coordinates.
    The WebSocket path (RiderLocationConsumer) is preferred.
    """

    permission_classes = [permissions.IsAuthenticated, IsRider]

    def post(self, request):
        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        RiderLocationService.update_location(
            rider=request.user,
            lat=serializer.validated_data["lat"],
            lng=serializer.validated_data["lng"],
        )

        return Response(
            {
                "detail": "Location updated.",
                "lat": serializer.validated_data["lat"],
                "lng": serializer.validated_data["lng"],
            },
            status=status.HTTP_200_OK,
        )
