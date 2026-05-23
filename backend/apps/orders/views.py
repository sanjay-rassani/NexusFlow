"""
Order views — four role tiers:

  Customer  — place, view, cancel own orders
  Vendor    — view incoming, accept/reject/prepare/mark-ready
  Rider     — view assigned, pickup/on-the-way/deliver
  Admin     — view all, assign riders
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminUser, IsCustomer, IsRider, IsVendor
from apps.vendors.services import VendorService

from .filters import OrderFilter
from .models import Order, OrderStatus
from .serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    OrderStatusNoteSerializer,
    RiderAssignSerializer,
)
from .services import OrderService


# ──────────────────────────────────────────────
# Customer views
# ──────────────────────────────────────────────

class CustomerOrderListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/orders/          — customer's own orders
    POST /api/v1/orders/          — place a new order
    """

    permission_classes = [permissions.IsAuthenticated, IsCustomer]
    filterset_class = OrderFilter
    ordering_fields = ["created_at", "total", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OrderCreateSerializer
        return OrderListSerializer

    def get_queryset(self):
        return (
            OrderService.get_order_queryset_base()
            .filter(customer=self.request.user)
        )

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = OrderService.create_order(request.user, serializer.validated_data)
        return Response(
            OrderDetailSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )


class CustomerOrderDetailView(APIView):
    """GET /api/v1/orders/{id}/ — customer views own order detail."""

    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def get(self, request, pk):
        order = OrderService.get_order_for_customer(pk, request.user)
        return Response(OrderDetailSerializer(order).data)


class CustomerOrderCancelView(APIView):
    """POST /api/v1/orders/{id}/cancel/ — customer cancels own order."""

    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def post(self, request, pk):
        order = OrderService.get_order_for_customer(pk, request.user)
        serializer = OrderStatusNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = OrderService.cancel_order(order, request.user)
        return Response(
            {
                "detail": "Order cancelled.",
                "order": OrderDetailSerializer(order).data,
            }
        )


# ──────────────────────────────────────────────
# Vendor views
# ──────────────────────────────────────────────

class VendorOrderListView(generics.ListAPIView):
    """GET /api/v1/orders/vendor/ — incoming orders for the vendor."""

    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendor]
    filterset_class = OrderFilter
    ordering_fields = ["created_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        vendor = VendorService.get_vendor_for_user(self.request.user)
        return OrderService.get_order_queryset_base().filter(vendor=vendor)


class _VendorOrderActionBase(APIView):
    """Shared logic for all vendor state-transition views."""

    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def _get_order(self, request, pk):
        vendor = VendorService.get_vendor_for_user(request.user)
        return OrderService.get_order_for_vendor(pk, vendor)

    def _transition(self, request, pk, action):
        order = self._get_order(request, pk)
        serializer = OrderStatusNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = action(order, request.user)
        return Response(OrderDetailSerializer(order).data)


class VendorAcceptOrderView(_VendorOrderActionBase):
    """POST /api/v1/orders/{id}/accept/  →  CREATED → ACCEPTED"""

    def post(self, request, pk):
        return self._transition(request, pk, OrderService.accept_order)


class VendorRejectOrderView(_VendorOrderActionBase):
    """POST /api/v1/orders/{id}/reject/  →  CREATED → CANCELLED (+ stock restore)"""

    def post(self, request, pk):
        return self._transition(request, pk, OrderService.reject_order)


class VendorPrepareOrderView(_VendorOrderActionBase):
    """POST /api/v1/orders/{id}/prepare/  →  ACCEPTED → PREPARING"""

    def post(self, request, pk):
        return self._transition(request, pk, OrderService.start_preparing)


class VendorReadyOrderView(_VendorOrderActionBase):
    """POST /api/v1/orders/{id}/ready/  →  PREPARING → READY_FOR_PICKUP"""

    def post(self, request, pk):
        return self._transition(request, pk, OrderService.mark_ready)


# ──────────────────────────────────────────────
# Rider views
# ──────────────────────────────────────────────

class RiderOrderListView(generics.ListAPIView):
    """GET /api/v1/orders/rider/ — orders assigned to this rider."""

    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated, IsRider]
    filterset_class = OrderFilter
    ordering = ["-created_at"]

    def get_queryset(self):
        return OrderService.get_order_queryset_base().filter(rider=self.request.user)


class _RiderOrderActionBase(APIView):
    permission_classes = [permissions.IsAuthenticated, IsRider]

    def _get_order(self, request, pk):
        return OrderService.get_order_for_rider(pk, request.user)

    def _transition(self, request, pk, action):
        order = self._get_order(request, pk)
        order = action(order, request.user)
        return Response(OrderDetailSerializer(order).data)


class RiderPickupOrderView(_RiderOrderActionBase):
    """POST /api/v1/orders/{id}/pickup/  →  READY_FOR_PICKUP → PICKED_UP"""

    def post(self, request, pk):
        return self._transition(request, pk, OrderService.pickup_order)


class RiderOnTheWayView(_RiderOrderActionBase):
    """POST /api/v1/orders/{id}/on-the-way/  →  PICKED_UP → ON_THE_WAY"""

    def post(self, request, pk):
        return self._transition(request, pk, OrderService.mark_on_the_way)


class RiderDeliverOrderView(_RiderOrderActionBase):
    """POST /api/v1/orders/{id}/deliver/  →  ON_THE_WAY → DELIVERED"""

    def post(self, request, pk):
        return self._transition(request, pk, OrderService.mark_delivered)


# ──────────────────────────────────────────────
# Admin views
# ──────────────────────────────────────────────

class AdminOrderListView(generics.ListAPIView):
    """GET /api/v1/orders/admin/ — all orders across the platform."""

    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    filterset_class = OrderFilter
    search_fields = ["customer__email", "vendor__name", "rider__email"]
    ordering_fields = ["created_at", "status", "total"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return OrderService.get_order_queryset_base().all()


class AdminOrderDetailView(APIView):
    """GET /api/v1/orders/admin/{id}/ — full order detail for admin."""

    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request, pk):
        try:
            order = OrderService.get_order_queryset_base().get(pk=pk)
        except Order.DoesNotExist:
            return Response(
                {"error": True, "code": "NOT_FOUND", "message": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(OrderDetailSerializer(order).data)


class AdminAssignRiderView(APIView):
    """POST /api/v1/orders/admin/{id}/assign-rider/ — admin assigns a rider."""

    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def post(self, request, pk):
        try:
            order = OrderService.get_order_queryset_base().get(pk=pk)
        except Order.DoesNotExist:
            return Response(
                {"error": True, "code": "NOT_FOUND", "message": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RiderAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rider = serializer.validated_data["rider_id"]  # resolve returns User object

        order = OrderService.assign_rider(order, rider, request.user)
        return Response(
            {
                "detail": f"Rider {rider.email} assigned to order {order.id}.",
                "order": OrderDetailSerializer(order).data,
            }
        )
