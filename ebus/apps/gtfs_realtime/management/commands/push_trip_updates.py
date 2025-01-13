import asyncio
from django.core.management.base import BaseCommand
import time
from gtfs_realtime.tasks import push_trip_updates_to_clients

class Command(BaseCommand):
    help = 'Runs shell with prepared algorithm'

    def handle(self, *args, **kwargs):
        counter = 1
        while True:
            try:
                asyncio.run(push_trip_updates_to_clients())
                print(f"wysłałem {counter} turę trip updates")
            except Exception as e:
                print(e)
            counter += 1
            time.sleep(5)