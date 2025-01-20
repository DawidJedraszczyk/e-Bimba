from django.contrib import admin
from django.urls import re_path, path, include
from .views import *
from django.conf import settings
import re


CITY_REGEX = "|".join(
    re.escape(city.value) for city in settings.CITY_ENUM
)

app_name='route_search'
urlpatterns = [
    path('', ChooseCityView.as_view(), name='ChooseCity'),
    re_path(rf'^(?P<city>{CITY_REGEX})/$', BaseView.as_view(), name='BaseView'),
    path('algorithm/find-route/<str:city_id>', FindRouteView.as_view(), name='FindRoute'),
]
