from django.urls import path

from .views import (
    AdminVendorActivateView,
    AdminVendorListView,
    PublicProductDetailView,
    PublicVendorDetailView,
    PublicVendorListView,
    PublicVendorProductListView,
    VendorCategoryDetailView,
    VendorCategoryListCreateView,
    VendorOnboardView,
    VendorProductDetailView,
    VendorProductListCreateView,
    VendorProfileView,
    VendorToggleOpenView,
)

urlpatterns = [
    # ── Public (customers) ────────────────────────────────────────────────
    path("", PublicVendorListView.as_view(), name="vendor-list"),
    path("<int:pk>/", PublicVendorDetailView.as_view(), name="vendor-detail"),
    path("<int:vendor_id>/products/", PublicVendorProductListView.as_view(), name="vendor-products"),

    # ── Vendor self-management ────────────────────────────────────────────
    path("onboard/", VendorOnboardView.as_view(), name="vendor-onboard"),
    path("me/", VendorProfileView.as_view(), name="vendor-me"),
    path("me/toggle-open/", VendorToggleOpenView.as_view(), name="vendor-toggle-open"),

    # ── Vendor product management ─────────────────────────────────────────
    path("me/products/", VendorProductListCreateView.as_view(), name="vendor-product-list"),
    path("me/products/<int:pk>/", VendorProductDetailView.as_view(), name="vendor-product-detail"),

    # ── Vendor category management ────────────────────────────────────────
    path("me/categories/", VendorCategoryListCreateView.as_view(), name="vendor-category-list"),
    path("me/categories/<int:pk>/", VendorCategoryDetailView.as_view(), name="vendor-category-detail"),

    # ── Admin ─────────────────────────────────────────────────────────────
    path("admin/", AdminVendorListView.as_view(), name="admin-vendor-list"),
    path("admin/<int:pk>/activate/", AdminVendorActivateView.as_view(), name="admin-vendor-activate"),
]

# Registered in config/urls.py as:
#   path("vendors/", include("apps.vendors.urls")),
# Which produces:
#   GET  /api/v1/vendors/
#   GET  /api/v1/vendors/{id}/
#   GET  /api/v1/vendors/{id}/products/
#   POST /api/v1/vendors/onboard/
#   GET/PATCH /api/v1/vendors/me/
#   POST /api/v1/vendors/me/toggle-open/
#   GET/POST  /api/v1/vendors/me/products/
#   GET/PATCH/DELETE /api/v1/vendors/me/products/{id}/
#   GET/POST  /api/v1/vendors/me/categories/
#   PATCH/DELETE /api/v1/vendors/me/categories/{id}/
#   GET  /api/v1/vendors/admin/
#   PATCH /api/v1/vendors/admin/{id}/activate/
