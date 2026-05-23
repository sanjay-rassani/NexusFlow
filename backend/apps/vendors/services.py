"""
Vendor and Product business logic service layer.

Key concurrency design:
  - Stock deduction uses SELECT FOR UPDATE inside a transaction to prevent
    overselling when multiple concurrent orders target the same product.
"""

import logging

from django.db import transaction
from rest_framework import serializers as drf_serializers

from core.cache import invalidate_product_cache, invalidate_vendor_cache

from .models import Product, ProductCategory, Vendor

logger = logging.getLogger(__name__)


class VendorService:

    @staticmethod
    def onboard(user, validated_data: dict) -> Vendor:
        """
        Create a vendor profile for a VENDOR-role user.
        Raises ValidationError if the user already has a profile or wrong role.
        """
        from apps.users.models import UserRole

        if user.role != UserRole.VENDOR:
            raise drf_serializers.ValidationError(
                {"detail": "Only users with the VENDOR role can onboard as a vendor."}
            )

        if Vendor.objects.filter(owner=user).exists():
            raise drf_serializers.ValidationError(
                {"detail": "You already have a vendor profile."}
            )

        vendor = Vendor.objects.create(owner=user, **validated_data)
        logger.info("Vendor onboarded: %s (owner=%s)", vendor.name, user.email)
        invalidate_vendor_cache()           # new vendor — invalidate list pages
        return vendor

    @staticmethod
    def update(vendor: Vendor, validated_data: dict) -> Vendor:
        for field, value in validated_data.items():
            setattr(vendor, field, value)
        vendor.save()
        logger.info("Vendor updated: %s", vendor.name)
        invalidate_vendor_cache(vendor.pk)
        return vendor

    @staticmethod
    def toggle_open(vendor: Vendor) -> Vendor:
        """Flip the is_open flag (kitchen open/closed)."""
        vendor.is_open = not vendor.is_open
        vendor.save(update_fields=["is_open", "updated_at"])
        state = "opened" if vendor.is_open else "closed"
        logger.info("Vendor %s %s.", vendor.name, state)
        invalidate_vendor_cache(vendor.pk)  # is_open appears in list view
        return vendor

    @staticmethod
    def set_active(vendor: Vendor, is_active: bool) -> Vendor:
        """Admin action — activate or deactivate a vendor account."""
        vendor.is_active = is_active
        vendor.save(update_fields=["is_active", "updated_at"])
        logger.info(
            "Vendor %s set to active=%s by admin.", vendor.name, is_active
        )
        invalidate_vendor_cache(vendor.pk)
        return vendor

    @staticmethod
    def get_vendor_for_user(user) -> Vendor:
        """
        Returns the vendor profile for the given user.
        Raises ValidationError if they don't have one.
        """
        try:
            return user.vendor_profile
        except Vendor.DoesNotExist:
            raise drf_serializers.ValidationError(
                {"detail": "You do not have a vendor profile. Please onboard first."}
            )


class ProductService:

    @staticmethod
    def create(vendor: Vendor, validated_data: dict) -> Product:
        product = Product.objects.create(vendor=vendor, **validated_data)
        logger.info("Product created: %s (vendor=%s)", product.name, vendor.name)
        invalidate_product_cache(vendor.pk, product.pk)
        return product

    @staticmethod
    def update(product: Product, validated_data: dict) -> Product:
        for field, value in validated_data.items():
            setattr(product, field, value)
        product.save()
        logger.info("Product updated: %s", product.name)
        invalidate_product_cache(product.vendor_id, product.pk)
        return product

    @staticmethod
    def delete(product: Product) -> None:
        """
        Soft delete — marks as unavailable rather than destroying the DB record.
        Hard-deleting would break historical order records.
        """
        product.is_available = False
        product.save(update_fields=["is_available", "updated_at"])
        logger.info("Product soft-deleted: %s", product.name)
        invalidate_product_cache(product.vendor_id, product.pk)

    @staticmethod
    @transaction.atomic
    def deduct_stock(product_id: int, quantity: int) -> bool:
        """
        Thread-safe stock deduction using SELECT FOR UPDATE.
        Returns True on success, False if insufficient stock.
        stock_count == 0 is treated as "unlimited" (no deduction).

        Called from OrderService in Phase 4 — never directly from views.
        """
        product = Product.objects.select_for_update().get(pk=product_id)

        if product.stock_count == 0:
            return True

        if product.stock_count < quantity:
            logger.warning(
                "Insufficient stock for product %s: requested=%d, available=%d",
                product.name,
                quantity,
                product.stock_count,
            )
            return False

        product.stock_count -= quantity
        if product.stock_count == 0:
            product.is_available = False

        product.save(update_fields=["stock_count", "is_available", "updated_at"])
        return True

    @staticmethod
    @transaction.atomic
    def restore_stock(product_id: int, quantity: int) -> None:
        """
        Return stock when an order is cancelled.
        Uses SELECT FOR UPDATE to prevent concurrent writes.
        """
        product = Product.objects.select_for_update().get(pk=product_id)

        if product.stock_count == 0:
            return

        product.stock_count += quantity
        product.is_available = True
        product.save(update_fields=["stock_count", "is_available", "updated_at"])
        logger.info(
            "Stock restored: %s +%d (total=%d)",
            product.name,
            quantity,
            product.stock_count,
        )


class ProductCategoryService:

    @staticmethod
    def create(vendor: Vendor, validated_data: dict) -> ProductCategory:
        category = ProductCategory.objects.create(vendor=vendor, **validated_data)
        logger.info(
            "Category created: %s (vendor=%s)", category.name, vendor.name
        )
        return category

    @staticmethod
    def update(category: ProductCategory, validated_data: dict) -> ProductCategory:
        for field, value in validated_data.items():
            setattr(category, field, value)
        category.save()
        return category

    @staticmethod
    def delete(category: ProductCategory) -> None:
        """
        Nullifies associated products' category FK (SET_NULL) rather than cascading.
        This preserves products when a category is removed.
        """
        category.delete()
        logger.info("Category deleted: %s", category.name)
