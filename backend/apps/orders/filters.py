"""
Order filtering — status, date range, vendor, rider.
"""

import django_filters
from django_filters import rest_framework as filters

from .models import Order, OrderStatus


class OrderFilter(filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=OrderStatus.choices)
    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    vendor = django_filters.NumberFilter(field_name="vendor__id")

    class Meta:
        model = Order
        fields = ["status", "vendor", "created_after", "created_before"]
