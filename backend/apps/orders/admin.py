from django.contrib import admin
from .models import Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["subtotal"]


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ["from_status", "to_status", "changed_by", "created_at"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "vendor", "status", "total", "created_at"]
    list_filter = ["status"]
    search_fields = ["id", "customer__email", "vendor__name"]
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    readonly_fields = ["id", "created_at", "updated_at"]
