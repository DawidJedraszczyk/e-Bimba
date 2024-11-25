from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/vehicle_positions/', consumers.VehiclePositionConsumer.as_asgi()),
    path('ws/trip_updates/', consumers.TripUpdatesConsumer.as_asgi()),
]