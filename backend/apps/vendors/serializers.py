"""
Vendor and Product serializers.

Separation pattern:
  - List serializers   — compact, used in collection responses (fewer fields, faster)
  - Detail serializers — full representation for single-object responses
  - Write serializers  — input validation for create/update operations
"""

from rest_framework import serializers

from .models import Product, ProductCategory, Vendor


# ──────────────────────────────────────────────
# ProductCategory
# ──────────────────────────────────────────────

class ProductCategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = ["id", "name", "order", "product_count"]
        read_only_fields = ["id"]

    def get_product_count(self, obj):
        return obj.products.filter(is_available=True).count()


class ProductCategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name", "order"]
        read_only_fields = ["id"]


# ──────────────────────────────────────────────
# Product
# ──────────────────────────────────────────────

class ProductListSerializer(serializers.ModelSerializer):
    """Compact — used in vendor product lists and customer browsing."""

    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
            "image",
            "is_available",
            "stock_count",
            "category",
            "category_name",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full product representation — used in single product GET."""

    category = ProductCategorySerializer(read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "image",
            "is_available",
            "stock_count",
            "category",
            "vendor",
            "vendor_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "vendor", "created_at", "updated_at"]


class ProductWriteSerializer(serializers.ModelSerializer):
    """Input validation for creating or updating a product."""

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "image",
            "is_available",
            "stock_count",
            "category",
        ]
        read_only_fields = ["id"]

    def validate_category(self, category):
        """Ensure the selected category belongs to the vendor making the request."""
        request = self.context.get("request")
        if category and request and hasattr(request.user, "vendor_profile"):
            if category.vendor != request.user.vendor_profile:
                raise serializers.ValidationError(
                    "Category does not belong to your vendor profile."
                )
        return category

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value


# ──────────────────────────────────────────────
# Vendor
# ──────────────────────────────────────────────

class VendorListSerializer(serializers.ModelSerializer):
    """Compact — used in the public vendor discovery list."""

    class Meta:
        model = Vendor
        fields = [
            "id",
            "name",
            "description",
            "logo",
            "address",
            "is_open",
            "phone_number",
        ]


class VendorDetailSerializer(serializers.ModelSerializer):
    """
    Full vendor representation — includes categories and product count.
    Used when a customer opens a vendor's page.
    Uses select_related/prefetch_related in the view to avoid N+1.
    """

    categories = ProductCategorySerializer(many=True, read_only=True)
    product_count = serializers.SerializerMethodField()
    owner_email = serializers.EmailField(source="owner.email", read_only=True)

    class Meta:
        model = Vendor
        fields = [
            "id",
            "name",
            "description",
            "logo",
            "address",
            "phone_number",
            "is_open",
            "is_active",
            "categories",
            "product_count",
            "owner_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]

    def get_product_count(self, obj):
        return obj.products.filter(is_available=True).count()


class VendorOnboardSerializer(serializers.ModelSerializer):
    """Used by a VENDOR-role user to create their vendor profile."""

    class Meta:
        model = Vendor
        fields = [
            "id",
            "name",
            "description",
            "address",
            "phone_number",
            "logo",
        ]
        read_only_fields = ["id"]


class VendorUpdateSerializer(serializers.ModelSerializer):
    """Allows vendor owners to update their profile (not ownership fields)."""

    class Meta:
        model = Vendor
        fields = [
            "name",
            "description",
            "address",
            "phone_number",
            "logo",
        ]
