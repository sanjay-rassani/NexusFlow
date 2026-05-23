"""
Notification REST endpoints.

All endpoints require authentication. Users can only access their own notifications.

GET  /api/v1/notifications/              — paginated list (filter ?is_read=true/false)
GET  /api/v1/notifications/unread-count/ — {"count": N}
POST /api/v1/notifications/{id}/read/   — mark single notification as read
POST /api/v1/notifications/read-all/    — mark all unread as read
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StandardResultsPagination

from .models import Notification
from .serializers import NotificationSerializer
from .services import NotificationService


class NotificationListView(generics.ListAPIView):
    """
    GET /api/v1/notifications/
    List authenticated user's notifications, newest first.
    Supports ?is_read=true or ?is_read=false to filter.
    """

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        is_read_param = self.request.query_params.get("is_read")
        is_read = None
        if is_read_param is not None:
            is_read = is_read_param.lower() in ("true", "1", "yes")
        return NotificationService.get_for_user(user=self.request.user, is_read=is_read)


class NotificationUnreadCountView(APIView):
    """
    GET /api/v1/notifications/unread-count/
    Returns the count of unread notifications for the authenticated user.
    Lightweight endpoint polled as a fallback when WebSocket is unavailable.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = NotificationService.get_unread_count(user=request.user)
        return Response({"count": count})


class NotificationMarkReadView(APIView):
    """
    POST /api/v1/notifications/{pk}/read/
    Mark a single notification as read.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        success = NotificationService.mark_read(notification_id=pk, user=request.user)
        if not success:
            return Response(
                {"error": True, "code": "NOT_FOUND", "message": "Notification not found or already read."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"detail": "Notification marked as read."})


class NotificationMarkAllReadView(APIView):
    """
    POST /api/v1/notifications/read-all/
    Mark all unread notifications for the current user as read.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        count = NotificationService.mark_all_read(user=request.user)
        return Response({"marked_count": count})
