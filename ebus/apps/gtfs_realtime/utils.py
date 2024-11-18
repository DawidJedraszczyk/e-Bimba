import requests
from google.transit import gtfs_realtime_pb2
import redis
from ebus.settings import REDIS_HOST, REDIS_PORT
import json

redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)
REDIS_VEHICLE_POSITIONS_KEY = "vehicle_positions"

def get_vehicle_positions():
    positions = redis_client.get(REDIS_VEHICLE_POSITIONS_KEY)
    return json.loads(positions) if positions else []


def fetch_gtfs_realtime_data(feed_url):
    response = requests.get(feed_url)
    if response.status_code == 200:
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        return feed
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")


def save_vehicle_positions(feed):
    vehicle_positions = []
    for entity in feed.entity:
        vehicle_data = entity.vehicle

        vehicle_position = {
            "route_id": vehicle_data.trip.route_id if vehicle_data.trip.HasField("route_id") else None,
            "trip_id": vehicle_data.trip.trip_id if vehicle_data.trip.HasField("trip_id") else None,
            "vehicle_id": vehicle_data.vehicle.id if vehicle_data.vehicle.HasField("id") else None,
            "latitude": vehicle_data.position.latitude if vehicle_data.position.HasField("latitude") else None,
            "longitude": vehicle_data.position.longitude if vehicle_data.position.HasField("longitude") else None,
            "timestamp": vehicle_data.timestamp if vehicle_data.HasField("timestamp") else None,
        }
        vehicle_positions.append(vehicle_position)

    redis_client.set(REDIS_VEHICLE_POSITIONS_KEY, json.dumps(vehicle_positions))


def save_trip_updates(feed):
    from .models import TripUpdate
    TripUpdate.objects.all().delete()

    for entity in feed.entity:
        trip_update = entity.trip_update

        for stop_time_update in trip_update.stop_time_update:
            vehicle = trip_update.vehicle


            TripUpdate.objects.create(
                trip_id=trip_update.trip.trip_id,
                route_id=trip_update.trip.route_id,
                vehicle_id=vehicle.id,
                stop_sequence=stop_time_update.stop_sequence,
                delay=stop_time_update.arrival.delay,
            )

