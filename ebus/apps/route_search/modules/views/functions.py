from django.templatetags.static import static

from algorithm.data import Data
from algorithm.utils import seconds_to_time


def plans_to_html(plans: list, data: Data):
    response = {}

    for index, plan in enumerate(plans):
        communication = []
        start_time = None
        destination_time = seconds_to_time(plan.time_at_destination)

        for plan_trip in plan.plan_trips:
            if plan_trip.trip_id != -1:
                if not start_time:
                    start_time = seconds_to_time(plan_trip.departure_time)

                route_id = data.trips[plan_trip.trip_id].route_id
                communication.append(data.routes[route_id].name)

        communication_content = ''
        for travel_option in communication:
            communication_content += f'''<div style="padding: 5px; display: flex; flex-direction: column; justify-content: center; align-items: center;"><img style="height: 23px; width: 23px; margin-bottom: 5px;" src="{static('base_view/img/BUS.svg')}">{str(travel_option)}</div>'''

        prepared_solution = {
            'div': f'''<div style="display:none"></div><div id="{index}" class="solution" style="cursor: pointer; width: 99%; border: solid 1px white; padding: 20px 0px; border-radius: 5px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;"> <div style="font-size: 25px; margin-left: 5px;">{start_time}</div><div style="display: flex;">{communication_content}</div><div style="font-size: 25px; margin-right: 5px;">{destination_time}</div></div>'''
        }
        response[str(index)] = prepared_solution
    return response


def prepare_coords(plan, start_coords, destination_coords, data: Data):
    response = {}

    for index, plan_trip in enumerate(plan.plan_trips):
        start_stop = data.stops[plan_trip.from_stop]
        goal_stop = data.stops[plan_trip.to_stop]

        if index == 0:
            response[0] = [(*start_coords,), (*start_stop.coords,)]

        if index == len(plan.plan_trips) - 1:
            response[len(plan.plan_trips) + 1] = [(*goal_stop.coords,), (*destination_coords,)]

        if plan_trip.trip_id != -1:
            trip = data.trips[plan_trip.trip_id]
            shape_id = trip.shape_id
            points = data.shapes.get_points_between(shape_id, start_stop.coords, goal_stop.coords)
            response[index + 1] = [(p.lat, p.lon) for p in points]
        else:
            response[index + 1] = [(*start_stop.coords,), (*goal_stop.coords,)]

    return response


def prepare_departure_details(plan, start_location: str, goal_location: str, data: Data):
    response = {}

    for index, plan_trip in enumerate(plan.plan_trips):
        start_stop = data.stops[plan_trip.from_stop]
        goal_stop = data.stops[plan_trip.to_stop]

        if index == 0:
            response[0] = f'''<div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;"><img style="width: 25px;" src="{static('base_view/img/WALK.png')}"><span style="margin-left: 10px; text-align: left;">{start_location} -> {start_stop.name}</span></div>'''

        if index == len(plan.plan_trips) - 1:
            response[len(plan.plan_trips) + 1] = f'''<div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;"><img style="width: 25px;" src="{static('base_view/img/WALK.png')}"><span style="margin-left: 10px; text-align: left;">{goal_stop.name} -> {goal_location}</span></div>'''

        departure_time = seconds_to_time(plan_trip.departure_time)
        arrival_time = seconds_to_time(plan_trip.arrival_time)

        if plan_trip.trip_id != -1:
            trip = data.trips[plan_trip.trip_id]
            route = data.routes[trip.route_id].name
            direction = trip.headsign


            response[index + 1] = f'''<div class="departure-details" style="display: flex; width: 90%; flex-direction: column; justify-content: center; margin: 10px 0;"><div style="display:flex; align-items: center; margin: 10px 0;"><img src="{static('base_view/img/BUS.svg')}" alt="bus icon"/><span style="margin-left: 10px;">{route} - {direction} ({departure_time} - {arrival_time})</span></div><div class="stops" style="font-size: 14px; text-align: left;">'''

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
                    response[index + 1] += f'''<div class="departure-time" data-sequence-number={stop_sequence}>{seconds_to_time(time)} {stop.name}</div>'''

                if stop_id == plan_trip.to_stop:
                    in_our_trip_flag = False

        else:
            response[index + 1] = f'''<div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;"><img style="width: 25px;" src="{static('base_view/img/WALK.png')}"><span style="margin-left: 10px; text-align: left;">{start_stop.name} -> {goal_stop.name}  ({departure_time} - {arrival_time})</span></div>'''

        response[index + 1] += "</div></div>"

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
