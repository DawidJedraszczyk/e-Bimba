from django.templatetags.static import static
import datetime
from algorithm.data import Data
from algorithm.utils import seconds_to_time


def plans_to_html(plans: list, data: Data, datetime: datetime.datetime):
    response = {}
    for index, plan in enumerate(plans):
        communication = []
        start_time = None
        destination_time = seconds_to_time(plan.time_at_destination, return_with_seconds=False)

        for plan_trip in plan.plan_trips:
            if plan_trip.trip_id != -1:
                if not start_time:
                    start_time = seconds_to_time(plan_trip.departure_time, return_with_seconds=False)

                route_id = data.trips[plan_trip.trip_id].route_id
                communication.append(data.routes[route_id].name)

        if not start_time and len(communication) == 0:
            start_time = datetime.time()
            communication = ['Spacerem']

        communication_content = ''
        for travel_option in communication:
            image = static('base_view/img/BUS.svg')
            if travel_option == 'Spacerem':
                image = static('base_view/img/WALK.png')
            communication_content += f'''<div style="padding: 5px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                <img style="height: 23px; width: 23px; margin-bottom: 5px;" src="{image}">{str(travel_option)}
            </div>'''

        prepared_solution = {
            'div': f'''<div style="display:none"></div>
            <div id="{index}" class="solution" 
                style="cursor: pointer; width: 99%; border: solid 1px white; padding: 20px 0px; border-radius: 5px; 
                margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;"
            > 
              <div style="font-size: 25px; margin-left: 5px;">{start_time}</div>
              <div style="display: flex;">{communication_content}</div>
              <div style="font-size: 25px; margin-right: 5px;">{destination_time}</div>
            </div>'''
        }
        response[str(index)] = prepared_solution
    return response


def prepare_coords_including_stops(plan, start_coords, destination_coords, data):
    response = {}

    for index, plan_trip in enumerate(plan.plan_trips):
        from_stop = data.stops[plan_trip.from_stop]
        to_stop = data.stops[plan_trip.to_stop]

        if index == 0:
            # Start
            response[0] = [
                {"kind": "start", "lat": start_coords[0], "lon": start_coords[1]},
                {"kind": "stop", "stop_id": plan_trip.from_stop,
                 "lat": from_stop.coords.lat, "lon": from_stop.coords.lon},
            ]

        if plan_trip.trip_id != -1:
            # Bus trip => call get_full_path_including_stops
            coords_list = get_full_path_including_stops(data, plan_trip)
            # coords_list is a list of {"kind": "stop"/"shape", "lat": ..., "lon": ..., "stop_id"?: ...}
            response[index + 1] = coords_list
        else:
            # Walking => direct line from from_stop to to_stop
            response[index + 1] = [
                {
                    "kind": "stop",
                    "stop_id": plan_trip.from_stop,
                    "lat": from_stop.coords.lat,
                    "lon": from_stop.coords.lon,
                },
                {
                    "kind": "stop",
                    "stop_id": plan_trip.to_stop,
                    "lat": to_stop.coords.lat,
                    "lon": to_stop.coords.lon,
                },
            ]

        if index == len(plan.plan_trips) - 1:
            # End
            response[len(plan.plan_trips) + 1] = [
                {
                    "kind": "stop",
                    "stop_id": plan_trip.to_stop,
                    "lat": to_stop.coords.lat,
                    "lon": to_stop.coords.lon,
                },
                {
                    "kind": "end",
                    "lat": destination_coords[0],
                    "lon": destination_coords[1],
                }
            ]

    # Edge case: If there are no plan_trips at all (pure walking)
    if len(plan.plan_trips) == 0:
        response[0] = [
            {"kind": "start", "lat": start_coords[0], "lon": start_coords[1]},
            {"kind": "end", "lat": destination_coords[0], "lon": destination_coords[1]},
        ]

    return response


def get_full_path_including_stops(data, plan_trip):
    """
    Returns a list of dictionaries, each describing a point:
      - "kind": "stop" or "shape"
      - "stop_id": (only if kind == "stop")
      - "lat": latitude
      - "lon": longitude

    This list includes every stop along the trip segment (from plan_trip.from_stop
    to plan_trip.to_stop) PLUS all shape points between those stops in order.
    """
    trip_id = plan_trip.trip_id
    from_stop_id = plan_trip.from_stop
    to_stop_id = plan_trip.to_stop

    # 1) Gather the ordered stops for this trip
    #    `get_trip_stops` usually returns a list of (stop_id, arrival_time, departure_time)
    trip_stops = data.trips.get_trip_stops(trip_id)
    stop_ids = [s[0] for s in trip_stops]  # just the stop IDs in sequence

    # 2) Locate which part of the trip is actually being used
    try:
        start_idx = stop_ids.index(from_stop_id)
        end_idx = stop_ids.index(to_stop_id)
    except ValueError:
        # If either from_stop or to_stop isn’t found in the trip’s sequence
        # (shouldn’t happen in a correct plan), return empty
        return []

    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx

    # 3) "Stitch" shape segments from `from_stop_id` to `to_stop_id`
    shape_id = data.trips[trip_id].shape_id
    full_path = []
    prev_stop_id = None

    for i in range(start_idx, end_idx + 1):
        current_stop_id = stop_ids[i]
        current_stop = data.stops[current_stop_id]

        if prev_stop_id is None:
            # This is the very first stop in our traveled segment
            full_path.append({
                "kind": "stop",
                "stop_id": current_stop_id,
                "lat": current_stop.coords.lat,
                "lon": current_stop.coords.lon
            })
            prev_stop_id = current_stop_id
            continue

        # Get shape points from the previous stop to the current stop
        previous_stop = data.stops[prev_stop_id]
        segment_points = data.shapes.get_points_between(
            shape_id, previous_stop.coords, current_stop.coords
        )
        # Typically, `segment_points` includes both the previous stop coords and the current stop coords.
        # We already have the previous stop in `full_path`, so skip the first point to avoid duplication.
        for p in segment_points[1:]:
            full_path.append({
                "kind": "shape",
                "lat": p.lat,
                "lon": p.lon
            })

        # Finally, add the current stop itself
        full_path.append({
            "kind": "stop",
            "stop_id": current_stop_id,
            "lat": current_stop.coords.lat,
            "lon": current_stop.coords.lon
        })

        prev_stop_id = current_stop_id

    return full_path


def prepare_departure_details(plan, start_location: str, goal_location: str, data: Data):
    response = {}

    for index, plan_trip in enumerate(plan.plan_trips):
        start_stop = data.stops[plan_trip.from_stop]
        goal_stop = data.stops[plan_trip.to_stop]

        if index == 0:
            response[
                0] = f'''<div style="display: flex; width: 90%; align-items: center; margin: 10px 0;">
                            <img style="width: 25px;" src="{static('base_view/img/WALK.png')}">
                            <span style="margin-left: 10px; text-align: left;">{start_stop.name}</span>
                        </div>'''

        if index == len(plan.plan_trips) - 1:
            response[
                len(plan.plan_trips) + 1] = f'''
                    <div style="display: flex; width: 90%; align-items: center; margin: 10px 0;">
                        <img style="width: 25px;" src="{static('base_view/img/WALK.png')}">
                        <span style="margin-left: 10px; text-align: left;">{goal_location}</span>
                    </div>'''

        departure_time = seconds_to_time(plan_trip.departure_time, return_with_seconds=False)
        arrival_time = seconds_to_time(plan_trip.arrival_time, return_with_seconds=False)

        if plan_trip.trip_id != -1:
            trip = data.trips[plan_trip.trip_id]
            route = data.routes[trip.route_id].name
            direction = trip.headsign

            response[index + 1] = f'''
                <ul class="timeline-with-icons departure-details">
                    <li class="timeline-item mb-5">
                      <span class="timeline-icon">
                        {departure_time}
                      </span>
                      <h5 class="fw-bold mb-0">{route} {direction} </h5>
                    </li>
                '''

            in_our_trip_flag = False
            time_offset = 0

            for stop_sequence, (stop_id, arrival, departure) in enumerate(data.trips.get_trip_stops(plan_trip.trip_id)):
                if stop_id == plan_trip.from_stop:
                    in_our_trip_flag = True
                    time_offset = departure
                    relevant_time = departure
                else:
                    relevant_time = arrival

                if in_our_trip_flag:
                    time = relevant_time - time_offset + plan_trip.departure_time
                    stop = data.stops[stop_id]
                    response[index + 1] += f'''
                            <li class="timeline-item mb-2 departure-time" data-sequence-number={stop_sequence}>
                                <span class="timeline-icon" style="font-size: 13px;">
                                    {seconds_to_time(time, return_with_seconds=False)}
                                </span>
                                <span style="font-size: 13px;">{stop.name}</span>
                            </li>
                        '''

                if stop_id == plan_trip.to_stop:
                    in_our_trip_flag = False

            response[index + 1] += "</ul>"

        else:
            response[index + 1] = f'''
                    <div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;">
                        <img style="width: 25px;" src="{static('base_view/img/WALK.png')}">
                         <span style="margin-left: 10px; text-align: left;">{start_stop.name} -> {goal_stop.name}  ({departure_time} - {arrival_time})</span>
                    </div>'''

    return response


def prepare_gtfs_trip_ids(plan, data: Data):
    response = {}

    for index, plan_trip in enumerate(plan.plan_trips):
        if plan_trip.trip_id != -1:
            response[index] = data.tdb.get_trip_instance(
                plan_trip.trip_id,
                plan_trip.service_id,
                plan_trip.trip_start
            ).gtfs_trip_id

    return response