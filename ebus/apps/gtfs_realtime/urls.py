from django.contrib import admin
from django.urls import path, include
from .views import *

app_name='gtfs_realtime'
urlpatterns = [
    path('vehicle_positions/', VehiclePositions, name='vehicle_positions'),

]
