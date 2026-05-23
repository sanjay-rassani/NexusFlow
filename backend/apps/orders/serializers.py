"""
Order serializers.

Separation:
  - OrderItemInputSerializer  — validates incoming item lines on order creation
  - OrderCreateSerializer     — validates the full order placement request
  - OrderItemSerializer       — represents a saved item (read-only)
  - OrderStatusHistorySerializer — represents audit trail entries
  - OrderListSerializer       — compact rows for list views
  - OrderDetailSerializer     — full order representation with items + history
"""

from decimal import Decimal

from rest_framework import serializers

from apps.vendors.models import Product, Vendor

from .models import Order, OrderItem, OrderStatus, OrderStatusHistory


# ──────────────────────────────────────────────
# Read-side serializers
# ──────────────────────────────────────────────

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_image = serializers.ImageField(source="product.image", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "product_image", "quantity", "unit_price", "subtotal"]


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = ["from_status", "to_status", "changed_by_email", "note", "created_at"]


class OrderListSerializer(serializers.ModelSerializer):
    """Compact — for list views across all roles."""

    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    rider_email = serializers.EmailField(source="rider.email", read_only=True, allow_null=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "vendor_name",
            "customer_email",
            "rider_email",
            "delivery_address",
            "subtotal",
            "delivery_fee",
            "total",
            "item_count",
            "created_at",
            "updated_at",
        ]

    def get_item_count(self, obj):
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Full order — includes items, status history, and rider info."""

    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    customer_name = serializers.SerializerMethodField()
    rider_name = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "vendor",
            "vendor_name",
            "customer",
            "customer_name",
            "rider",
            "rider_name",
            "delivery_address",
            "special_instructions",
            "subtotal",
            "delivery_fee",
            "total",
            "estimated_delivery_time",
            "items",
            "status_history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_customer_name(self, obj):
        return obj.customer.full_name or obj.customer.email

    def get_rider_name(self, obj):
        if obj.rider:
            return obj.rider.full_name or obj.rider.email
        return None


# ──────────────────────────────────────────────
# Write-side serializers
# ──────────────────────────────────────────────

class OrderItemInputSerializer(serializers.Serializer):
    """Validates a single item line in an order placement request."""

    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=100)

    def validate(self, data):
        product = data["product"]
        if not product.is_available:
            raise serializers.ValidationError(
                {"product": f"'{product.name}' is not currently available."}
            )
        if product.stock_count > 0 and product.stock_count < data["quantity"]:
            raise serializers.ValidationError(
                {
                    "quantity": (
                        f"Only {product.stock_count} unit(s) of '{product.name}' in stock."
                    )
                }
            )
        return data


class OrderCreateSerializer(serializers.Serializer):
    """
    Validates the full order placement payload.

    Expected input:
    {
        "vendor": 1,
        "delivery_address": "123 Main St",
        "special_instructions": "No onions",
        "items": [
            {"product": 1, "quantity": 2},
            {"product": 3, "quantity": 1}
        ]
    }
    """

    vendor = serializers.PrimaryKeyRelatedField(
        queryset=Vendor.objects.filter(is_active=True, is_open=True)
    )
    delivery_address = serializers.CharField(min_length=5)
    special_instructions = serializers.CharField(required=False, allow_blank=True, default="")
    delivery_fee = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, default=Decimal("0.00")
    )
    items = OrderItemInputSerializer(many=True, min_length=1)

    def validate(self, data):
        vendor = data["vendor"]
        items = data["items"]

        # All items must belong to the chosen vendor
        for item_data in items:
            product = item_data["product"]
            if product.vendor != vendor:
                raise serializers.ValidationError(
                    {
                        "items": (
                            f"Product '{product.name}' does not belong to the selected vendor."
                        )
                    }
                )

        return data


class RiderAssignSerializer(serializers.Serializer):
    """Admin assigns a rider to an order."""

    rider_id = serializers.UUIDField()

    def validate_rider_id(self, value):
        from apps.users.models import User, UserRole

        try:
            rider = User.objects.get(pk=value, role=UserRole.RIDER, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("No active rider found with this ID.")
        return rider


class OrderStatusNoteSerializer(serializers.Serializer):
    """Optional note attached to any status transition."""

    note = serializers.CharField(required=False, allow_blank=True, default="")
