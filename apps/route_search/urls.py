from django.contrib import admin
from django.urls import path, include
from .views import *

app_name='route_search'
urlpatterns = [
    path('', BaseView.as_view(), name='BaseView'),
    path('find-route/', FindRouteView.as_view(), name='FindRoute'),
    path('get-stops-coords/', GetCoordsView.as_view(), name='GetCoords'),
    path('get-departure-hours/', GetDepartureHoursView.as_view(), name='GetDepartureHours'),
    path('get-buses/', GetBusesView.as_view(), name='GetBuses'),
]
