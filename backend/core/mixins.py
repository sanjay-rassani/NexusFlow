"""
Reusable ViewSet mixins for consistent API patterns.
"""

from rest_framework.response import Response
from rest_framework import status


class SerializerActionMixin:
    """
    Allow ViewSets to declare a dict of serializers per action.

    Usage:
        serializer_classes = {
            'list': OrderListSerializer,
            'retrieve': OrderDetailSerializer,
            'create': OrderCreateSerializer,
        }
        default_serializer_class = OrderListSerializer
    """

    serializer_classes = {}
    default_serializer_class = None

    def get_serializer_class(self):
        return self.serializer_classes.get(
            self.action, self.default_serializer_class or super().get_serializer_class()
        )


class SoftDeleteMixin:
    """
    Soft-delete instead of hard DELETE.
    Requires the model to have `is_active` boolean field.
    """

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)
