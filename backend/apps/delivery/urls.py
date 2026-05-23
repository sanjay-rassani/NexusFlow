from django.urls import path
from .views import RiderLocationUpdateView

urlpatterns = [
    # REST fallback — primary path is WebSocket (ws/rider/{id}/location/)
    path("location/", RiderLocationUpdateView.as_view(), name="rider-location-update"),
]
