from django.db import models

class TripUpdate(models.Model):
    trip_id = models.CharField(max_length=255)
    route_id = models.CharField(max_length=50)
    vehicle_id = models.CharField(max_length=50)

    stop_sequence = models.DecimalField(max_digits=3, decimal_places=0)
    delay = models.DecimalField(max_digits=10, decimal_places=0)
    created_at = models.DateTimeField(auto_now_add=True)


class VehiclePosition(models.Model):
    trip_id = models.CharField(max_length=50)
    route_id = models.CharField(max_length=50)
    vehicle_id = models.CharField(max_length=50)

    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
