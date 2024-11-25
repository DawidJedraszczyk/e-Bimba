from django.contrib import admin
from .models import VehiclePosition

@admin.register(VehiclePosition)
class VehiclePositionAdmin(admin.ModelAdmin):
    list_display = ('vehicle_id', 'latitude', 'longitude', 'timestamp')
