import datetime
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
from algorithm.astar_planner import AStarPlanner
from algorithm.utils import time_to_seconds
from transit.data.misc import Coords


r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
geolocator = Nominatim(user_agent="ebus")


def load_cities_data():
    with open(settings.CITIES_JSON_PATH, 'r', encoding='utf-8') as file:
        cities_data = json.load(file)
    return cities_data

cities = load_cities_data()

def get_city_id(request_path):
    for city in cities:
        for key, value in city.items():
            if key =='name' and value.lower() in request_path.lower():
                return city['id']

def load_city_data(city_id):
    return Data.instance(Path.cwd().parent / "data" / "cities" / f"{city_id}.db")


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
        city_full_name = kwargs['city']
        city_id = get_city_id(city_full_name)
        data = load_city_data(city_id)
        context['city_id'] = city_id
        context['city_name'] = city_full_name
        context['center_coordinates'] = [*data.md.center_coords]
        return context


class FindRouteView(View):

    def post(self, request, *args, **kwargs):
        city_id = kwargs['city_id']
        data = load_city_data(city_id)

        start_name, start_latitude, start_longitude = json.loads(request.POST.get('start_location')).values()
        destination_name, destination_latitude, destination_longitude = json.loads(request.POST.get('goal_location')).values()

        _datetime = datetime.datetime.strptime(request.POST.get('datetime'), '%Y-%m-%dT%H:%M')

        planner = AStarPlanner(
            data,
            Coords(start_latitude, start_longitude),
            Coords(destination_latitude, destination_longitude),
            _datetime.date(),
            time_to_seconds(_datetime.strftime("%H:%M:%S")),
            data.default_estimator,
        )

        for _ in range(5):
            planner.find_next_plan()

        prospect = planner.prospect
        plans = planner.found_plans
        html = plans_to_html(planner.found_plans, data, _datetime)
        coords = {
            i: prepare_coords(plan, prospect.start_coords, prospect.destination_coords, data)
            for i, plan in enumerate(plans)
        }
        details = {
            i: prepare_departure_details(plan, start_name, destination_name, data)
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
