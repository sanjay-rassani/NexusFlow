"""
Standalone product URL — public product detail by ID.
Mounted at /api/v1/products/ in the root URL config.
"""

from django.urls import path

from .views import PublicProductDetailView

urlpatterns = [
    path("<int:pk>/", PublicProductDetailView.as_view(), name="product-detail"),
]
