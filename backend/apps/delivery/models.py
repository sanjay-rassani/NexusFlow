"""
Delivery and RiderLocation models.
Full implementation in Phase 4.
"""

from django.conf import settings
from django.db import models


class RiderProfile(models.Model):
    """Extended profile for delivery riders."""

    rider = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rider_profile",
        limit_choices_to={"role": "RIDER"},
    )
    vehicle_type = models.CharField(
        max_length=50,
        choices=[("BIKE", "Bike"), ("CAR", "Car"), ("SCOOTER", "Scooter")],
        default="BIKE",
    )
    vehicle_plate = models.CharField(max_length=20, blank=True)
    is_available = models.BooleanField(default=True)
    current_lat = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    current_lng = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rider_profiles"

    def __str__(self):
        return f"Rider: {self.rider.email}"


class RiderLocationHistory(models.Model):
    """
    Time-series table for rider GPS coordinates.
    Used for live tracking and route replay.
    High-write table — consider TimescaleDB in production.
    """

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="location_history",
        limit_choices_to={"role": "RIDER"},
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rider_locations",
    )
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rider_location_history"
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["rider", "recorded_at"]),
            models.Index(fields=["order"]),
        ]
