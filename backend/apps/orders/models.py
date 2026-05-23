"""
Order and OrderItem models.
Full state machine logic implemented in Phase 4.
"""

import uuid

from django.conf import settings
from django.db import models


class OrderStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    ACCEPTED = "ACCEPTED", "Accepted"
    PREPARING = "PREPARING", "Preparing"
    READY_FOR_PICKUP = "READY_FOR_PICKUP", "Ready for Pickup"
    PICKED_UP = "PICKED_UP", "Picked Up"
    ON_THE_WAY = "ON_THE_WAY", "On the Way"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"


# Valid state transitions — enforced in the service layer
ORDER_STATUS_TRANSITIONS = {
    OrderStatus.CREATED: [OrderStatus.ACCEPTED, OrderStatus.CANCELLED],
    OrderStatus.ACCEPTED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
    OrderStatus.PREPARING: [OrderStatus.READY_FOR_PICKUP],
    OrderStatus.READY_FOR_PICKUP: [OrderStatus.PICKED_UP],
    OrderStatus.PICKED_UP: [OrderStatus.ON_THE_WAY],
    OrderStatus.ON_THE_WAY: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
}


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        limit_choices_to={"role": "CUSTOMER"},
    )
    vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries",
        limit_choices_to={"role": "RIDER"},
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.CREATED,
    )
    delivery_address = models.TextField()
    special_instructions = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["vendor", "status"]),
            models.Index(fields=["rider", "status"]),
        ]

    def __str__(self):
        return f"Order {self.id} — {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "vendors.Product", on_delete=models.PROTECT, related_name="order_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "order_items"

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} (Order {self.order.id})"


class OrderStatusHistory(models.Model):
    """Audit trail for all order status transitions."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_status_history"
        ordering = ["created_at"]
