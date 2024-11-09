from django.views.generic import TemplateView
from django.http import JsonResponse
from geopy.geocoders import Nominatim
from .modules.algorithm_parts.utils import *
from .modules.algorithm_parts.AstarPlanner import *
from django.http import HttpResponse
from django.views import View
import redis
import pickle
from ebus.settings import REDIS_HOST, REDIS_PORT

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
geolocator = Nominatim(user_agent="ebus")


class BaseView(TemplateView):
    '''
    Simple view which map and searching engine. In this view we can search for bus route and find the best bus
    that we want to use.
    Also in future #TODO there will be a schedule
    '''

    template_name = 'base_view/index.html'

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class FindRouteView(View):
    def post(self, request, *args, **kwargs):
        start_time = time_to_seconds(request.POST.get('time')+":00")

        start = geolocator.geocode(request.POST.get('start_location') + ', Poznań, województwo wielkopolskie, Polska')
        destination = geolocator.geocode(request.POST.get('goal_location') + ', Poznań, województwo wielkopolskie, Polska')

        planner_straight = AStarPlanner(start_time, (start.latitude, start.longitude), (destination.latitude, destination.longitude), 'manhattan', '2024-09-05')

        for _ in range(20):
            planner_straight.find_next_plan()

        html = planner_straight.plans_to_html()

        coords = {}
        for solution_id in range(len(planner_straight.found_plans)):
            coords[solution_id] = planner_straight.prepare_coords(solution_id)

        details = {}
        for solution_id in range(len(planner_straight.found_plans)):
            details[solution_id] = planner_straight.prepare_departure_details(solution_id, start,destination)


        response_data = {
            'html': html,
            'coords': coords,
            'details': details
        }
        return JsonResponse(response_data)
