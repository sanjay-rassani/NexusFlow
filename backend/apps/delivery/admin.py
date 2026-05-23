from django.contrib import admin
from .models import RiderLocationHistory, RiderProfile


@admin.register(RiderProfile)
class RiderProfileAdmin(admin.ModelAdmin):
    list_display = ["rider", "vehicle_type", "is_available", "current_lat", "current_lng"]
    list_filter = ["vehicle_type", "is_available"]


@admin.register(RiderLocationHistory)
class RiderLocationHistoryAdmin(admin.ModelAdmin):
    list_display = ["rider", "order", "lat", "lng", "recorded_at"]
    list_filter = ["rider"]
    readonly_fields = ["recorded_at"]
