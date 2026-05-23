"""
Django-filter filterset classes for Vendor and Product list endpoints.
"""

import django_filters
from django_filters import rest_framework as filters

from .models import Product, Vendor


class VendorFilter(filters.FilterSet):
    """
    Filters for the public vendor list.
    Customers can filter by open status and search by name.
    """

    name = django_filters.CharFilter(lookup_expr="icontains")
    is_open = django_filters.BooleanFilter()

    class Meta:
        model = Vendor
        fields = ["name", "is_open"]


class ProductFilter(filters.FilterSet):
    """
    Filters for product list views.
    Supports price range, category, availability, and name search.
    """

    name = django_filters.CharFilter(lookup_expr="icontains")
    category = django_filters.NumberFilter(field_name="category__id")
    is_available = django_filters.BooleanFilter()
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Product
        fields = ["name", "category", "is_available", "min_price", "max_price"]
