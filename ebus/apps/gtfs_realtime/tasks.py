from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from .utils import fetch_gtfs_realtime_data, save_vehicle_positions, save_trip_updates
from django.conf import settings
import json

def load_cities_data():
    with open(settings.CITIES_JSON_PATH, 'r', encoding='utf-8') as file:
        cities_data = json.load(file)
    return cities_data

cities = load_cities_data()
realtime_urls = [{'city_name': city['name'], 'urls': city['realtime']} for city in cities if city.get('realtime')]

async def push_vehicle_positions_to_clients():
    for realtime in realtime_urls:
        city = realtime['city_name']
        feed_url = realtime['urls']['vehicle_updates']

        feed = await sync_to_async(fetch_gtfs_realtime_data)(feed_url)
        await sync_to_async(save_vehicle_positions)(feed, city)

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        "vehicle_positions",
        {
            "type": "send_positions",
            "message": "New vehicle positions available",
        },
    )

async def push_trip_updates_to_clients():
    for realtime in realtime_urls:
        city = realtime['city_name']
        feed_url = realtime['urls']['trip_updates']

        feed = await sync_to_async(fetch_gtfs_realtime_data)(feed_url)
        await sync_to_async(save_trip_updates)(feed, city)

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        "trip_updates",
        {
            "type": "send_trip_updates",
            "message": "New trip updates available"
        }
    )