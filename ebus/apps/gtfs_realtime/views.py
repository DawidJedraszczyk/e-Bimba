from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import render
from django.http import JsonResponse
from .models import VehiclePosition, TripUpdate

def VehiclePositions(request):
    positions = VehiclePosition.objects.all()
    data = [
        {
            "vehicle_id": pos.vehicle_id,
            "latitude": pos.latitude,
            "longitude": pos.longitude,
            "timestamp": pos.timestamp,
        }
        for pos in positions
    ]
    return JsonResponse(data, safe=False)

def TripUpdates(request):
    updates = TripUpdate.objects.all()
    data = [
        {
            "trip_id": pos.trip_id,
            "stop_id": pos.stop_id,
            "arrival_time": pos.arrival_time,
            "departure_time": pos.departure_time,
        }
        for pos in updates
    ]
    return JsonResponse(data, safe=False)