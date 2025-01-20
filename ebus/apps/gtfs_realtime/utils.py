import requests
from google.transit import gtfs_realtime_pb2
import redis
from ebus.settings import REDIS_HOST, REDIS_PORT
import json

redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)
REDIS_VEHICLE_POSITIONS_KEY = "vehicle_positions"
REDIS_TRIP_UPDATES_KEY = "trip_updates"

def get_vehicle_positions():
    positions = redis_client.get(REDIS_VEHICLE_POSITIONS_KEY)
    return json.loads(positions) if positions else []


def get_trip_updates():
    updates = redis_client.get(REDIS_TRIP_UPDATES_KEY)
    return json.loads(updates) if updates else []


def fetch_gtfs_realtime_data(feed_url):
    response = requests.get(feed_url)
    if response.status_code == 200:
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        return feed
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")


def save_vehicle_positions(feed, city):
    current_data = redis_client.get(REDIS_VEHICLE_POSITIONS_KEY)
    if current_data:
        vehicle_positions = json.loads(current_data)
    else:
        vehicle_positions = {}

    vehicle_positions[city] = []
    for entity in feed.entity:
        vehicle_data = entity.vehicle

        vehicle_position = {
            "route_id": vehicle_data.trip.route_id,
            "trip_id": vehicle_data.trip.trip_id,
            "vehicle_id": vehicle_data.vehicle.id,
            "latitude": vehicle_data.position.latitude,
            "longitude": vehicle_data.position.longitude,
            "timestamp": vehicle_data.timestamp,
        }
        vehicle_positions[city].append(vehicle_position)

    redis_client.set(REDIS_VEHICLE_POSITIONS_KEY, json.dumps(vehicle_positions))


def save_trip_updates(feed, city):
    current_data = redis_client.get(REDIS_TRIP_UPDATES_KEY)
    if current_data:
        trip_updates = json.loads(current_data)
    else:
        trip_updates = {}

    trip_updates[city] = []
    for entity in feed.entity:
        trip_update_data = entity.trip_update

        for stop_time_update in trip_update_data.stop_time_update:
            trip_update = {
                "trip_id": trip_update_data.trip.trip_id,
                "route_id": trip_update_data.trip.route_id,
                "vehicle_id": trip_update_data.vehicle.id,
                "stop_sequence": stop_time_update.stop_sequence,
                "delay": stop_time_update.arrival.delay,
            }
            trip_updates[city].append(trip_update)

    redis_client.set(REDIS_TRIP_UPDATES_KEY, json.dumps(trip_updates))
