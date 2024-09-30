from django.views.generic import TemplateView
from django.http import JsonResponse
from geopy.geocoders import Nominatim
from .modules.views.functions import *
from .modules.algorithm.algorithm import *
from django.http import HttpResponse
from django.views import View
import json
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

        planner_straight = AStarPlanner(start_time, (start.latitude, start.longitude), (destination.latitude, destination.longitude), 'manhattan')

        for _ in range(20):
            planner_straight.find_next_plan()

        response = plans_to_html(planner_straight.found_plans)  # prepare_response(algorithm_results)


        if not request.session.session_key:
            request.session.save()
        session_key = request.session.session_key
        serialized_planner = pickle.dumps(planner_straight)
        redis_key = f'planner_straight_{session_key}'
        r.set(redis_key, serialized_planner)
        r.expire(redis_key, 3600)

        return JsonResponse(response)


class GetCoordsView(View):
    def post(self, request, *args, **kwargs):

        if not request.session.session_key:
            return HttpResponse("Sesja nie została znaleziona.")

        session_key = request.session.session_key
        redis_key = f'planner_straight_{session_key}'
        serialized_planner = r.get(redis_key)

        if serialized_planner:
            data = json.loads(request.body)
            solution_id = int(data['solution_id'])

            planner_straight = pickle.loads(serialized_planner)

            return JsonResponse(prepare_coords(planner_straight, solution_id))
        else:
            return HttpResponse("Dane nie zostały znalezione w pamięci podręcznej.")


class GetDepartureHoursView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        #solution_id = data.get('solution_id')
        #algorithm_response = request.session.get('algorithm_response')

        #bus_departures = algorithm_response[solution_id]

        #response = prepare_departure_hours(bus_departures)

        return '' #JsonResponse(response)

class GetBusesView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        solution_id = data.get('solution_id')
        algorithm_response = request.session.get('algorithm_response')

        #bus_departures = algorithm_response[solution_id]

        response = ''# prepare_buses(bus_departures)

        return JsonResponse(response)

