from channels.generic.websocket import AsyncWebsocketConsumer
from .models import VehiclePosition, TripUpdate
from asgiref.sync import sync_to_async
import json
from .utils import get_vehicle_positions, get_trip_updates


class VehiclePositionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "vehicle_positions"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_positions(self, event):
        vehicle_positions = await sync_to_async(get_vehicle_positions)()
        data = {}
        for city, positions in vehicle_positions.items():
            city_data = [
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
            data[city] = city_data

        await self.send(text_data=json.dumps(data))


class TripUpdatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "trip_updates"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_trip_updates(self, event):
        trip_updates = await sync_to_async(get_trip_updates)()
        data = {}
        for city, trips in trip_updates.items():
            city_data = [
                {
                    "trip_id": update["trip_id"],
                    "route_id": update["route_id"],
                    "vehicle_id": update["vehicle_id"],
                    "stop_sequence": float(update["stop_sequence"]),
                    "delay": float(update["delay"]),
                }
                for update in trips
            ]
            data[city] = city_data
        await self.send(text_data=json.dumps(data))
