from django.contrib import admin
from django.urls import re_path, path, include
from .views import *
from django.conf import settings
import re


CITY_REGEX = "|".join(
    re.escape(city.value) for city in settings.CITY_ENUM
)
# Iterate through the CITY_ENUM to print all cities
for city in settings.CITY_ENUM:
    print(city.name, city.value)

print("Generated CITY_REGEX:", CITY_REGEX)


app_name='route_search'
urlpatterns = [
    re_path(rf'^(?P<city>{CITY_REGEX})/$', BaseView.as_view(), name='BaseView'),
    path('algorithm/find-route/<str:city_id>', FindRouteView.as_view(), name='FindRoute'),
]
