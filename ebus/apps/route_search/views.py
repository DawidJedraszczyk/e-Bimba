from datetime import datetime
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView
from geopy.geocoders import Nominatim
import json
from pathlib import Path
import redis
import sys

from .modules.views.functions import *
from algorithm.estimator import ManhattanEstimator
from algorithm.astar_planner import AStarPlanner
from algorithm.utils import time_to_seconds
from ebus.settings import REDIS_HOST, REDIS_PORT
from transit.data.misc import Coords


r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
geolocator = Nominatim(user_agent="ebus")


def load_city_data(city):
    return Data.instance(Path.cwd().parent / "data" / "cities" / f"{city}.db")


class BaseView(TemplateView):
    '''
    Simple view which map and searching engine. In this view we can search for bus route and find the best bus
    that we want to use.
    Also in future #TODO there will be a schedule
    '''

    template_name = 'base_view/index.html'

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        city_id = kwargs['city']
        data = load_city_data(city_id)
        context['city'] = city_id
        context['center_coordinates'] = [*data.md.center_coords]
        return context


class FindRouteView(View):

    def post(self, request, *args, **kwargs):
        city_id = request.POST.get('city')
        data = load_city_data(city_id)
        city = data.md.name

        start = geolocator.geocode(request.POST.get('start_location') + ',' + city +', Polska')
        destination = geolocator.geocode(request.POST.get('goal_location') + ',' + city + ', Polska')

        _datetime = datetime.strptime(request.POST.get('datetime'), '%Y-%m-%dT%H:%M')

        planner = AStarPlanner(
            data,
            Coords(start.latitude, start.longitude),
            Coords(destination.latitude, destination.longitude),
            _datetime.strftime("%Y-%m-%d"),
            time_to_seconds(_datetime.strftime("%H:%M:%S")),
            data.estimator_factory,
        )

        for _ in range(5):
            planner.find_next_plan()

        prospect = planner.prospect
        plans = planner.found_plans
        html = plans_to_html(planner.found_plans, data)

        coords = {
            i: prepare_coords(plan, prospect.start_coords, prospect.destination_coords, data)
            for i, plan in enumerate(plans)
        }

        details = {
            i: prepare_departure_details(plan, start, destination, data)
            for i, plan in enumerate(plans)
        }

        gtfs = {
            i: prepare_gtfs_trip_ids(plan, data)
            for i, plan in enumerate(plans)
        }

        response_data = {
            'html': html,
            'coords': coords,
            'details': details,
            'gtfs': gtfs
        }
        return JsonResponse(response_data)
