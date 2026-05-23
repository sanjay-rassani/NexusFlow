"""
Vendor and Product views — three access tiers:

  1. Public (customers) — read-only, active vendors + available products
  2. Vendor-gated      — manage own profile, products, categories
  3. Admin             — manage all vendors (activate/deactivate)
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.cache import (
    CacheKeys,
    TTL_PRODUCT_LIST,
    TTL_VENDOR_DETAIL,
    TTL_VENDOR_LIST,
)
from core.mixins import SerializerActionMixin
from core.permissions import IsAdminUser, IsVendor

from .filters import ProductFilter, VendorFilter
from .models import Product, ProductCategory, Vendor
from .serializers import (
    ProductCategorySerializer,
    ProductCategoryWriteSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductWriteSerializer,
    VendorDetailSerializer,
    VendorListSerializer,
    VendorOnboardSerializer,
    VendorUpdateSerializer,
)
from .services import ProductCategoryService, ProductService, VendorService


# ──────────────────────────────────────────────
# Public — Customers browsing vendors/products
# ──────────────────────────────────────────────

class PublicVendorListView(generics.ListAPIView):
    """
    GET /api/v1/vendors/
    Lists all active vendors. Filterable by name, is_open.
    Cached per unique query-param combination for TTL_VENDOR_LIST seconds.
    """

    serializer_class = VendorListSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = VendorFilter
    search_fields = ["name", "description", "address"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return Vendor.objects.filter(is_active=True).order_by("name")

    def list(self, request, *args, **kwargs):
        from django.core.cache import cache

        cache_key = CacheKeys.vendor_list(request.query_params)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=TTL_VENDOR_LIST)
        return response


class PublicVendorDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/vendors/{id}/
    Full vendor detail including categories.
    Cached per vendor_id for TTL_VENDOR_DETAIL seconds.
    """

    serializer_class = VendorDetailSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Vendor.objects.filter(is_active=True).prefetch_related(
            "categories", "categories__products"
        )

    def retrieve(self, request, *args, **kwargs):
        from django.core.cache import cache

        cache_key = CacheKeys.vendor_detail(kwargs["pk"])
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=TTL_VENDOR_DETAIL)
        return response


class PublicVendorProductListView(generics.ListAPIView):
    """
    GET /api/v1/vendors/{vendor_id}/products/
    Lists all available products for a vendor.
    Cached per (vendor_id, query params) for TTL_PRODUCT_LIST seconds.
    """

    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "name", "created_at"]
    ordering = ["category__order", "name"]

    def get_queryset(self):
        return (
            Product.objects.filter(
                vendor_id=self.kwargs["vendor_id"],
                vendor__is_active=True,
                is_available=True,
            )
            .select_related("category")
            .order_by("category__order", "name")
        )

    def list(self, request, *args, **kwargs):
        from django.core.cache import cache

        cache_key = CacheKeys.vendor_products(
            kwargs["vendor_id"], request.query_params
        )
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=TTL_PRODUCT_LIST)
        return response


class PublicProductDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/products/{id}/
    Single product detail (public).
    """

    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Product.objects.filter(
            vendor__is_active=True, is_available=True
        ).select_related("category", "vendor")


# ──────────────────────────────────────────────
# Vendor — manage own profile
# ──────────────────────────────────────────────

class VendorOnboardView(APIView):
    """
    POST /api/v1/vendors/onboard/
    A VENDOR-role user creates their vendor profile (one-time setup).
    """

    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def post(self, request):
        serializer = VendorOnboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vendor = VendorService.onboard(request.user, serializer.validated_data)
        return Response(
            VendorDetailSerializer(vendor).data,
            status=status.HTTP_201_CREATED,
        )


class VendorProfileView(APIView):
    """
    GET  /api/v1/vendors/me/  — retrieve own vendor profile
    PATCH /api/v1/vendors/me/ — update own vendor profile
    """

    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def _get_vendor(self, user):
        return VendorService.get_vendor_for_user(user)

    def get(self, request):
        vendor = self._get_vendor(request.user)
        return Response(
            VendorDetailSerializer(vendor, context={"request": request}).data
        )

    def patch(self, request):
        vendor = self._get_vendor(request.user)
        serializer = VendorUpdateSerializer(
            vendor, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        vendor = VendorService.update(vendor, serializer.validated_data)
        return Response(VendorDetailSerializer(vendor, context={"request": request}).data)


class VendorToggleOpenView(APIView):
    """
    POST /api/v1/vendors/me/toggle-open/
    Flip the vendor's is_open flag (kitchen open/closed).
    """

    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def post(self, request):
        vendor = VendorService.get_vendor_for_user(request.user)
        vendor = VendorService.toggle_open(vendor)
        return Response(
            {
                "id": vendor.id,
                "name": vendor.name,
                "is_open": vendor.is_open,
                "detail": f"Vendor is now {'open' if vendor.is_open else 'closed'}.",
            }
        )


# ──────────────────────────────────────────────
# Vendor — manage own products
# ──────────────────────────────────────────────

class VendorProductListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/vendors/me/products/  — list own products (all, including unavailable)
    POST /api/v1/vendors/me/products/  — create a new product
    """

    permission_classes = [permissions.IsAuthenticated, IsVendor]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "name", "is_available", "created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProductWriteSerializer
        return ProductListSerializer

    def get_queryset(self):
        vendor = VendorService.get_vendor_for_user(self.request.user)
        return (
            Product.objects.filter(vendor=vendor)
            .select_related("category")
            .order_by("category__order", "name")
        )

    def perform_create(self, serializer):
        vendor = VendorService.get_vendor_for_user(self.request.user)
        ProductService.create(vendor, serializer.validated_data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        vendor = VendorService.get_vendor_for_user(request.user)
        product = ProductService.create(vendor, serializer.validated_data)
        return Response(
            ProductDetailSerializer(product, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class VendorProductDetailView(APIView):
    """
    GET    /api/v1/vendors/me/products/{id}/  — product detail
    PATCH  /api/v1/vendors/me/products/{id}/  — update product
    DELETE /api/v1/vendors/me/products/{id}/  — soft-delete product
    """

    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def _get_product(self, user, pk):
        vendor = VendorService.get_vendor_for_user(user)
        try:
            return Product.objects.select_related("category", "vendor").get(
                pk=pk, vendor=vendor
            )
        except Product.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Product not found.")

    def get(self, request, pk):
        product = self._get_product(request.user, pk)
        return Response(
            ProductDetailSerializer(product, context={"request": request}).data
        )

    def patch(self, request, pk):
        product = self._get_product(request.user, pk)
        serializer = ProductWriteSerializer(
            product,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        product = ProductService.update(product, serializer.validated_data)
        return Response(
            ProductDetailSerializer(product, context={"request": request}).data
        )

    def delete(self, request, pk):
        product = self._get_product(request.user, pk)
        ProductService.delete(product)
        return Response(
            {"detail": f"Product '{product.name}' has been removed from your catalog."},
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────
# Vendor — manage own categories
# ──────────────────────────────────────────────

class VendorCategoryListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/vendors/me/categories/  — list own categories
    POST /api/v1/vendors/me/categories/  — create a category
    """

    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProductCategoryWriteSerializer
        return ProductCategorySerializer

    def get_queryset(self):
        vendor = VendorService.get_vendor_for_user(self.request.user)
        return ProductCategory.objects.filter(vendor=vendor).order_by("order")

    def create(self, request, *args, **kwargs):
        serializer = ProductCategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vendor = VendorService.get_vendor_for_user(request.user)
        category = ProductCategoryService.create(vendor, serializer.validated_data)
        return Response(
            ProductCategorySerializer(category).data,
            status=status.HTTP_201_CREATED,
        )


class VendorCategoryDetailView(APIView):
    """
    PATCH  /api/v1/vendors/me/categories/{id}/  — update category
    DELETE /api/v1/vendors/me/categories/{id}/  — delete category
    """

    permission_classes = [permissions.IsAuthenticated, IsVendor]

    def _get_category(self, user, pk):
        vendor = VendorService.get_vendor_for_user(user)
        try:
            return ProductCategory.objects.get(pk=pk, vendor=vendor)
        except ProductCategory.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Category not found.")

    def patch(self, request, pk):
        category = self._get_category(request.user, pk)
        serializer = ProductCategoryWriteSerializer(
            category, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        category = ProductCategoryService.update(category, serializer.validated_data)
        return Response(ProductCategorySerializer(category).data)

    def delete(self, request, pk):
        category = self._get_category(request.user, pk)
        name = category.name
        ProductCategoryService.delete(category)
        return Response(
            {"detail": f"Category '{name}' deleted."},
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────
# Admin — vendor management
# ──────────────────────────────────────────────

class AdminVendorListView(generics.ListAPIView):
    """
    GET /api/v1/vendors/admin/
    Lists all vendors (active + inactive) for admin oversight.
    """

    serializer_class = VendorDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    search_fields = ["name", "owner__email", "address"]
    ordering_fields = ["name", "is_active", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Vendor.objects.all().select_related("owner").prefetch_related("categories")


class AdminVendorActivateView(APIView):
    """
    PATCH /api/v1/vendors/admin/{id}/activate/
    Body: {"is_active": true/false}
    """

    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def patch(self, request, pk):
        try:
            vendor = Vendor.objects.get(pk=pk)
        except Vendor.DoesNotExist:
            return Response(
                {"error": True, "code": "NOT_FOUND", "message": "Vendor not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_active = request.data.get("is_active")
        if is_active is None:
            return Response(
                {"error": True, "code": "VALIDATION_ERROR", "message": "'is_active' field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vendor = VendorService.set_active(vendor, bool(is_active))
        return Response(
            {
                "id": vendor.id,
                "name": vendor.name,
                "is_active": vendor.is_active,
                "detail": f"Vendor {'activated' if vendor.is_active else 'deactivated'}.",
            }
        )
