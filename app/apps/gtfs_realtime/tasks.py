from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from .utils import fetch_gtfs_realtime_data, save_vehicle_positions, save_trip_updates


async def push_vehicle_positions_to_clients():
    feed_url = "https://www.ztm.poznan.pl/pl/dla-deweloperow/getGtfsRtFile?file=vehicle_positions.pb"
    feed = await sync_to_async(fetch_gtfs_realtime_data)(feed_url)

    await sync_to_async(save_vehicle_positions)(feed)

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        "vehicle_positions",
        {
            "type": "send_positions",
            "message": "New vehicle positions available",
        },
    )

async def push_trip_updates_to_clients():
    feed_url = "https://www.ztm.poznan.pl/pl/dla-deweloperow/getGtfsRtFile?file=trip_updates.pb"
    feed = await sync_to_async(fetch_gtfs_realtime_data)(feed_url)
    await sync_to_async(save_trip_updates)(feed)

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        "trip_updates",
        {
            "type": "send_trip_updates",
            "message": "New trip updates available"
        }
    )
