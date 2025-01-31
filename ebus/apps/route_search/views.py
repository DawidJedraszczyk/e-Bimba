import datetime
from django.conf import settings
from django.http import JsonResponse, Http404
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView
from geopy.geocoders import Nominatim
import json
from pathlib import Path
import redis
import sys
from .modules.views.functions import *
from algorithm.astar_planner import AStarPlanner
from algorithm.preferences import Preferences
from algorithm.utils import time_to_seconds
from tickets.models import TicketType, Ticket
from transit.data.misc import Coords, Delays


r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
geolocator = Nominatim(user_agent="ebus")


def load_cities_data():
    with open(settings.CITIES_JSON_PATH, 'r', encoding='utf-8') as file:
        cities_data = json.load(file)
    return cities_data

cities = load_cities_data()

def get_city(request_path_city):
    for city in cities:
        for key, value in city.items():
            if key == 'name' and value.lower() == request_path_city:
                return city

def load_city_data(city_id):
    if city_id:
        return Data.instance(Path.cwd().parent / "data" / "cities" / f"{city_id}.db")
    return None


class BaseView(TemplateView):
    template_name = 'base_view/index.html'

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        city_full_name = kwargs.get('city')

        # Validate city against the Enum
        if city_full_name not in [city.value for city in settings.CITY_ENUM]:
            raise Http404(_(f"City '{city_full_name}' is not valid."))

        city = get_city(city_full_name)
        city_id = city['id']
        data = load_city_data(city_id)
        if not data:
            raise Http404(_(f"No data found for city: {city_full_name}"))

        ticket_types = TicketType.active_tickets.all()
        ticket_types_by_category = {}

        for ticket in ticket_types:
            if ticket.category not in ticket_types_by_category:
                ticket_types_by_category[ticket.category] = []
            ticket_types_by_category[ticket.category].append(ticket)

        context['cities'] = cities
        context['city_id'] = city_id
        context['city_name'] = city_full_name.capitalize()
        context['tickets_available'] = city['tickets']
        context['center_coordinates'] = [*data.md.center_coords]
        context['ticket_types_by_category'] = ticket_types_by_category
        context['mapbox_access_token'] = settings.MAPBOX_ACCESS_TOKEN
        return context

class ChooseCityView(TemplateView):
    template_name = 'choose_city_view/index.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cities'] = cities
        return context

class FindRouteView(View):

    def post(self, request, *args, **kwargs):
        city_id = kwargs['city_id']
        data = load_city_data(city_id)

        try:
            start_name, start_latitude, start_longitude = json.loads(request.POST.get('start_location')).values()
            destination_name, destination_latitude, destination_longitude = json.loads(request.POST.get('goal_location')).values()
        except (ValueError, KeyError):
            return JsonResponse({'error': _('Invalid start or destination location data.')}, status=400)

        try:
            _datetime = datetime.datetime.strptime(request.POST.get('datetime'), '%d-%m-%Y %H:%M')
        except ValueError:
            return JsonResponse({'error': _('Invalid date and time format.')}, status=400)

        if request.user and request.user.is_authenticated:
            preferences = Preferences(
                pace=request.user.pace,
                max_distance=request.user.max_distance,
            )
        else:
            preferences = Preferences()

        trip_updates = r.get("trip_updates")

        if trip_updates:
            delays = data.tdb.process_delays(trip_updates.decode("utf-8"))
        else:
            delays = Delays.empty()

        planner = AStarPlanner(
            data,
            Coords(start_latitude, start_longitude),
            Coords(destination_latitude, destination_longitude),
            _datetime.date(),
            time_to_seconds(_datetime.strftime("%H:%M:%S")),
            data.default_estimator,
            preferences,
            delays,
        )

        for _ in range(5):
            planner.find_next_plan()

        prospect = planner.prospect
        plans = planner.found_plans

        html = plans_to_html(planner.found_plans, data, _datetime)

        coords = {
            i: prepare_coords_including_stops(plan, prospect.start_coords, prospect.destination_coords, data)
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
            'gtfs': gtfs,
        }
        return JsonResponse(response_data)
