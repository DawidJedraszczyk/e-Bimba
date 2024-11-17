import requests
from google.transit import gtfs_realtime_pb2

def fetch_gtfs_realtime_data(feed_url):
    response = requests.get(feed_url)
    if response.status_code == 200:
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        return feed
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")

def save_vehicle_positions(feed):
    from .models import VehiclePosition
    VehiclePosition.objects.all().delete()

    for entity in feed.entity:
        vehicle = entity.vehicle

        VehiclePosition.objects.create(
            vehicle_id=vehicle.vehicle.id,
            latitude=vehicle.position.latitude,
            longitude=vehicle.position.longitude,
            route_id=vehicle.trip.route_id,
            trip_id=vehicle.trip.trip_id,
        )


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

