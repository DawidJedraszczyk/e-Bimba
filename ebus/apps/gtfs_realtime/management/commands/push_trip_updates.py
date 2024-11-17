import asyncio
from django.core.management.base import BaseCommand
from gtfs_realtime.tasks import push_trip_updates_to_clients

class Command(BaseCommand):
    help = 'Runs shell with prepared algorithm'

    def handle(self, *args, **kwargs):
        asyncio.run(push_trip_updates_to_clients())