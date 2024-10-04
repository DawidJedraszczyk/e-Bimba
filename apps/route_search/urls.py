from django.contrib import admin
from django.urls import path, include
from .views import *

app_name='route_search'
urlpatterns = [
    path('', BaseView.as_view(), name='BaseView'),
    path('find-route/', FindRouteView.as_view(), name='FindRoute'),
    path('get-stops-coords/', GetCoordsView.as_view(), name='GetCoords'),
    path('get-departures-details/', GetDeparturesDetailsView.as_view(), name='GetDepartureDetails'),
]
