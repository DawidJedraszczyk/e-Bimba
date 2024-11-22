from django.views.generic import TemplateView
from django.http import JsonResponse
from geopy.geocoders import Nominatim
from .modules.algorithm_parts.utils import *
from .modules.algorithm_parts.AstarPlanner import *
from .modules.algorithm_parts.estimator import ManhattanEstimator
from django.views import View
import redis
from ebus.settings import REDIS_HOST, REDIS_PORT
from django.conf import settings
from datetime import datetime
import json
from pathlib import Path
from bimba.data.misc import Coords
import sys


ROOT = Path(__file__).parents[3]
sys.path.extend([
  str(ROOT),
  str(ROOT / "ebus"),
  str(ROOT / "ebus" / "apps" / "route_search" / "modules"),
  str(ROOT / "pipeline"),
])

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
geolocator = Nominatim(user_agent="ebus")


def load_cities_data():
    with open(settings.CITIES_JSON_PATH, 'r', encoding='utf-8') as file:
        cities_data = json.load(file)
    return cities_data

cities = load_cities_data()

def get_city(request_path):
    for city, data in cities.items():
        if city.lower() in request_path.lower():
            return city.capitalize()

def get_coords(request_path):
    for city, data in cities.items():
        if city.lower() in request_path.lower():
            coordinates = data.get("center_coordinates")
            return [coordinates["lng"], coordinates["lat"]]

    return None

class BaseView(TemplateView):
    '''
    Simple view which map and searching engine. In this view we can search for bus route and find the best bus
    that we want to use.
    Also in future #TODO there will be a schedule
    '''

    template_name = 'base_view/index.html'

    def get(self, request, *args, **kwargs):

        return super().get(request, *args, **kwargs)

    def get_context_data(self,*args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['city'] = get_city(self.request.path)
        context['center_coordinates'] = get_coords(self.request.path)
        return context


class FindRouteView(View):

    def post(self, request, *args, **kwargs):
        city = get_city(request.POST.get('city'))
        database_name = cities[city]['database']
        data = Data.instance(ROOT / "data" / "cities" / database_name)

        start = geolocator.geocode(request.POST.get('start_location') + ',' + city +', Polska')
        destination = geolocator.geocode(request.POST.get('goal_location') + ',' + city + ', Polska')

        _datetime = datetime.strptime(request.POST.get('datetime'), '%Y-%m-%dT%H:%M')

        planner_straight = AStarPlanner(
            data,
            Coords(*(start.latitude, start.longitude)),
            Coords(*(destination.latitude, destination.longitude)),
            _datetime.strftime("%Y-%m-%d"),
            time_to_seconds(_datetime.strftime("%H:%M:%S")),
            ManhattanEstimator,
        )

        for _ in range(5):
            planner_straight.find_next_plan()
        html = planner_straight.plans_to_html()

        coords = {}
        for solution_id in range(len(planner_straight.found_plans)):
            coords[solution_id] = planner_straight.prepare_coords(solution_id)

        details = {}
        gtfs = {}
        for solution_id in range(len(planner_straight.found_plans)):
            details[solution_id] = planner_straight.prepare_departure_details(solution_id, start,destination)
            gtfs[solution_id] = planner_straight.prepare_gtfs_trip_ids(solution_id)


        response_data = {
            'html': html,
            'coords': coords,
            'details': details,
            'gtfs': gtfs
        }
        return JsonResponse(response_data)
