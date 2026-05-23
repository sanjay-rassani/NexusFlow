"""
Vendor and Product models.
Full implementation in Phase 3.
"""

from django.db import models
from django.conf import settings


class Vendor(models.Model):
    """A vendor (restaurant/shop) on the platform."""

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vendor_profile",
        limit_choices_to={"role": "VENDOR"},
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    address = models.TextField()
    phone_number = models.CharField(max_length=20)
    logo = models.ImageField(upload_to="vendors/logos/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendors"
        indexes = [models.Index(fields=["is_active", "is_open"])]

    def __str__(self):
        return self.name


class ProductCategory(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "product_categories"
        ordering = ["order"]

    def __str__(self):
        return f"{self.vendor.name} — {self.name}"


class Product(models.Model):
    """A product/menu item offered by a vendor."""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(
        ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    is_available = models.BooleanField(default=True)
    stock_count = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        indexes = [
            models.Index(fields=["vendor", "is_available"]),
        ]

    def __str__(self):
        return f"{self.vendor.name} — {self.name}"
