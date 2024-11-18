from channels.generic.websocket import AsyncWebsocketConsumer
from .models import VehiclePosition, TripUpdate
from asgiref.sync import sync_to_async
import json
from .utils import get_vehicle_positions


class VehiclePositionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "vehicle_positions"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_positions(self, event):
        positions = await sync_to_async(get_vehicle_positions)()

        data = [
            {
                "route_id": pos["route_id"],
                "trip_id": pos["trip_id"],
                "vehicle_id": pos["vehicle_id"],
                "latitude": pos["latitude"],
                "longitude": pos["longitude"],
                "timestamp": pos["timestamp"],
            }
            for pos in positions
        ]
        await self.send(text_data=json.dumps(data))


class TripUpdatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "trip_updates"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_trip_updates(self, event):
        trip_updates = await sync_to_async(list)(TripUpdate.objects.all())
        data = [
            {
                "trip_id": pos.trip_id,
                "route_id": pos.route_id,
                "vehicle_id": pos.vehicle_id,
                "stop_sequence": float(pos.stop_sequence),
                "delay": float(pos.delay),
            }
            for pos in trip_updates
        ]
        await self.send(text_data=json.dumps(data))
