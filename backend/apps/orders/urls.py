from django.urls import path

from .views import (
    AdminAssignRiderView,
    AdminOrderDetailView,
    AdminOrderListView,
    CustomerOrderCancelView,
    CustomerOrderDetailView,
    CustomerOrderListCreateView,
    RiderDeliverOrderView,
    RiderOnTheWayView,
    RiderOrderListView,
    RiderPickupOrderView,
    VendorAcceptOrderView,
    VendorOrderListView,
    VendorPrepareOrderView,
    VendorReadyOrderView,
    VendorRejectOrderView,
)

urlpatterns = [
    # ── Customer ─────────────────────────────────────────────────────────
    path("", CustomerOrderListCreateView.as_view(), name="order-list-create"),
    path("<uuid:pk>/", CustomerOrderDetailView.as_view(), name="order-detail"),
    path("<uuid:pk>/cancel/", CustomerOrderCancelView.as_view(), name="order-cancel"),

    # ── Vendor ───────────────────────────────────────────────────────────
    path("vendor/", VendorOrderListView.as_view(), name="vendor-order-list"),
    path("<uuid:pk>/accept/", VendorAcceptOrderView.as_view(), name="order-accept"),
    path("<uuid:pk>/reject/", VendorRejectOrderView.as_view(), name="order-reject"),
    path("<uuid:pk>/prepare/", VendorPrepareOrderView.as_view(), name="order-prepare"),
    path("<uuid:pk>/ready/", VendorReadyOrderView.as_view(), name="order-ready"),

    # ── Rider ────────────────────────────────────────────────────────────
    path("rider/", RiderOrderListView.as_view(), name="rider-order-list"),
    path("<uuid:pk>/pickup/", RiderPickupOrderView.as_view(), name="order-pickup"),
    path("<uuid:pk>/on-the-way/", RiderOnTheWayView.as_view(), name="order-on-the-way"),
    path("<uuid:pk>/deliver/", RiderDeliverOrderView.as_view(), name="order-deliver"),

    # ── Admin ────────────────────────────────────────────────────────────
    path("admin/", AdminOrderListView.as_view(), name="admin-order-list"),
    path("admin/<uuid:pk>/", AdminOrderDetailView.as_view(), name="admin-order-detail"),
    path("admin/<uuid:pk>/assign-rider/", AdminAssignRiderView.as_view(), name="admin-assign-rider"),
]
