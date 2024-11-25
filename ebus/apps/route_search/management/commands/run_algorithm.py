from django.core.management.base import BaseCommand
import code
import django
import os
import sys
import datetime

class Command(BaseCommand):
    help = 'Runs shell with prepared algorithm'

    def handle(self, *args, **options):
        # Set up the Django environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings')
        django.setup()

        # Prepare the locals dictionary with your imports
        local_vars = {}

        try:
            from route_search.modules.algorithm_parts.AstarPlanner import AStarPlanner
            from route_search.modules.algorithm_parts.utils import time_to_seconds
            from geopy.geocoders import Nominatim

            start_time = time_to_seconds("16:00:00")
            geolocator = Nominatim(user_agent="ebus")

            start = geolocator.geocode('Jana Kochanowskiego 1, Poznań, województwo wielkopolskie, Polska')
            destination = geolocator.geocode('Marcelińska 27, Poznań, województwo wielkopolskie, Polska')

            planner_straight = AStarPlanner(start_time, (start.latitude, start.longitude),
                                            (destination.latitude, destination.longitude), 'manhattan', '2024-10-21')

            for _ in range(20):
                planner_straight.find_next_plan()
            local_vars.update(locals())

        except ImportError as e:
            self.stderr.write(self.style.ERROR(f'Error importing modules: {e}'))
            sys.exit(1)

        try:
            from IPython.terminal.embed import InteractiveShellEmbed
            shell = InteractiveShellEmbed()
            shell(local_ns=local_vars)
        except ImportError:
            code.interact(local=local_vars)
