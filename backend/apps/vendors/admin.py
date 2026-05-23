from django.contrib import admin
from .models import Product, ProductCategory, Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "is_active", "is_open", "created_at"]
    list_filter = ["is_active", "is_open"]
    search_fields = ["name", "owner__email"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "vendor", "price", "is_available", "stock_count"]
    list_filter = ["is_available", "vendor"]
    search_fields = ["name", "vendor__name"]


admin.site.register(ProductCategory)
