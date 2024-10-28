import datetime
from haversine import haversine, Unit
from .DataLoaderSingleton import initialized_dataloader_singleton
from .AstarPlanner import AStarPlanner
from ebus.algorithm_settings import PRINTING_SETTINGS
from django.templatetags.static import static


def get_date_service_id(date_str):
    return get_date_service_id_for_Poznan(date_str)


def get_date_service_id_for_Poznan(date_str):
    """
    Return the day type for a given date in Poznan.
    Parameters:
    date_str (str): The date in 'YYYY-MM-DD'
    Returns:
    int: The day type according to the notation used in Poznan GTFS data
    """
    # FIXME - use actual GTFS file  encoding daytypes instead of hardcoded values (will be usefull for adding more cities)
    day_type_dict = {
        'Monday': 5,
        'Tuesday': 1,
        'Wednesday': 1,
        'Thursday': 1,
        'Friday': 7,
        'Saturday': 3,
        'Sunday': 4
    }
    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    day_of_week = date_obj.strftime('%A')

    return day_type_dict[day_of_week]


def get_previous_day(date_str):
    """
    Return the date of the day before the given date.
    Parameters:
    date_str (str): The date in 'YYYY-MM-DD'
    Returns:
    str: The date of the day before in 'YYYY-MM-DD'
    """
    # Parse the date string into a datetime object
    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')

    # Subtract one day from the date
    previous_date_obj = date_obj - datetime.timedelta(days=1)

    # Convert the datetime object back to a string
    previous_date_str = previous_date_obj.strftime('%Y-%m-%d')

    return previous_date_str


def get_next_day(date_str):
    """
    Return the date of the day before the given date.
    Parameters:
    date_str (str): The date in 'YYYY-MM-DD'
    Returns:
    str: The date of the day before in 'YYYY-MM-DD'
    """
    # Parse the date string into a datetime object
    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')

    # Subtract one day from the date
    previous_date_obj = date_obj + datetime.timedelta(days=1)

    # Convert the datetime object back to a string
    previous_date_str = previous_date_obj.strftime('%Y-%m-%d')

    return previous_date_str


def time_to_seconds(time_str: str) -> int:
    """Maps time from HH:MM:SS format to total no. of seconds"""
    hms = [int(i) for i in time_str.split(':')]
    return hms[0] * 3600 + hms[1] * 60 + hms[2]


def seconds_to_time(time_seconds) -> str:
    """Maps time from total no. of seconds to HH:MM:SS format"""
    time_seconds = int(time_seconds)
    hours = time_seconds // 3600
    time_seconds %= 3600
    minutes = time_seconds // 60
    time_seconds %= 60
    return f"{hours:02}:{minutes:02}:{time_seconds:02}"


def custom_print(message, level='DEFAULT'):
    if PRINTING_SETTINGS[level]:
        print(f"[{level}] {message}")


def manhattan_distance(
        lat1: float, lon1: float,
        lat2: float, lon2: float
) -> float:
    # haversine - works like euclidean, but considers earth's curvature
    distance_across_latitude = haversine((lat1, lon1), (lat2, lon1), unit=Unit.METERS)
    distance_across_longitude = haversine((lat1, lon1), (lat1, lon2), unit=Unit.METERS)
    return distance_across_latitude + distance_across_longitude


def plans_to_string(found_plans):
    result = ""
    for i, plan in enumerate(found_plans):
        result += '\t-----------------\n'
        result += f'\tPlan {i}\n'
        result += "\t" + str(plan).replace("\n", "\n\t") + "\n"
    return result

def plans_to_html(found_plans):
    response = {}
    trips = initialized_dataloader_singleton.get_trips()

    for index, plan in enumerate(found_plans):
        communication = []
        start_time = None
        destination_time = seconds_to_time(plan.time_at_destination)

        for plan_trip in plan.plan_trips:
            if not plan_trip.type == 'WALK':
                trip_from_df = trips[trips['trip_id'] == plan_trip.trip_id].iloc[0]
                if not start_time:
                    start_time = seconds_to_time(plan_trip.departure_time)

                communication.append(trip_from_df['route_id'])


        communication_content = ''
        for travel_option in communication:
            communication_content += f'''<div style="padding: 5px; display: flex; flex-direction: column; justify-content: center; align-items: center;"><img style="height: 23px; width: 23px; margin-bottom: 5px;" src="{static('base_view/img/BUS.svg')}">{str(travel_option)}</div>'''

        prepared_solution = {
            'div': f'''<div style="display:none"></div>
                       <div id="{index}" class="solution" style="cursor: pointer; width: 99%; border: solid 1px white; padding: 20px 0px; border-radius: 5px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                           <div style="font-size: 25px; margin-left: 5px;">{start_time}</div>
                           <div style="display: flex;">{communication_content}</div>
                           <div style="font-size: 25px; margin-right: 5px;">{destination_time}</div>
                       </div>
                    '''
        }
        response[str(index)] = prepared_solution
    return response


def get_lat_lon_sets(shape_id):
    _all_shapes_df = initialized_dataloader_singleton.get_shapes_df()
    shapes = _all_shapes_df[_all_shapes_df['shape_id'] == shape_id]

    lat_lon_sets = [(row['shape_pt_lat'], row['shape_pt_lon']) for _, row in shapes.iterrows()]

    return lat_lon_sets

def find_closest_shape_point(stop_lat, stop_lon, shape_points):
    closest_point = None
    closest_distance = float('inf')

    for shape_point in shape_points:
        point_lat, point_lon = shape_point
        distance = haversine((stop_lat, stop_lon), (point_lat, point_lon), Unit.METERS)

        if distance < closest_distance:
            closest_distance = distance
            closest_point = shape_point

    return closest_point


def prepare_coords(astarplaner: AStarPlanner, plan_num: int):
    response = {}
    stops = initialized_dataloader_singleton.get_stops()
    trips = initialized_dataloader_singleton.get_trips()
    shapes = initialized_dataloader_singleton.get_shapes()


    plan = astarplaner.found_plans[plan_num]


    for index, plan_trip in enumerate(plan.plan_trips):
        if index == 0:
            start_stop = stops[stops['stop_id'] == plan_trip.start_from_stop_id].iloc[0]
            response[0] = [astarplaner.start, (start_stop.stop_lat, start_stop.stop_lon)]

        if index == len(plan.plan_trips) - 1:
            goal_stop = stops[stops['stop_id'] == plan_trip.leave_at_stop_id].iloc[0]
            response[len(plan.plan_trips)+1] = [(goal_stop.stop_lat, goal_stop.stop_lon), astarplaner.destination]


        response[index+1] = []
        sequence_numbers = []

        if plan_trip.trip_id:
            trip = trips[plan_trip.trip_id]
            shape_id = int(trips[trips['trip_id'] == plan_trip.trip_id].iloc[0].shape_id)
            lat_lon_sets = get_lat_lon_sets(shape_id)
            trip_stops = [stops[stop_id] for stop_id in trip.stop_ids]


            for stop in trip_stops:
                if stop.stop_id == plan_trip.start_from_stop_id or stop.stop_id == plan_trip.leave_at_stop_id:

                    closest_point = find_closest_shape_point(stop.stop_lat, stop.stop_lon, lat_lon_sets)

                    closest_lat, closest_lon = closest_point  # Tuple unpacking should match the lat-lon order

                    filtered_shape = shapes[
                        (shapes['shape_id'] == shape_id) &
                        (shapes['shape_pt_lat'] == closest_lat) &
                        (shapes['shape_pt_lon'] == closest_lon)
                    ]

                    if not filtered_shape.empty:
                        seq_num = int(filtered_shape['shape_pt_sequence'].iloc[0])
                        sequence_numbers.append(seq_num)

            if sequence_numbers:
                min_seq_num = min(sequence_numbers)
                max_seq_num = max(sequence_numbers)

                matching_shapes = shapes[
                    (shapes['shape_id'] == shape_id) &
                    (shapes['shape_pt_sequence'] >= min_seq_num) &
                    (shapes['shape_pt_sequence'] <= max_seq_num)
                ]

                lat_lon_pairs = list(zip(matching_shapes['shape_pt_lat'], matching_shapes['shape_pt_lon']))

                response[index+1] = lat_lon_pairs

        else:
            start_stop = stops[stops['stop_id'] == plan_trip.start_from_stop_id].iloc[0]
            goal_stop = stops[stops['stop_id'] == plan_trip.leave_at_stop_id].iloc[0]

            response[index+1] = [(start_stop.stop_lat, start_stop.stop_lon), (goal_stop.stop_lat, goal_stop.stop_lon)]

    return response

def prepare_departure_details(astarplaner: AStarPlanner, plan_num: int, start_location: str, goal_location: str):
    response = {}
    stops = initialized_dataloader_singleton.get_stops()
    trips = initialized_dataloader_singleton.get_trips()


    plan = astarplaner.found_plans[plan_num]

    for index, plan_trip in enumerate(plan.plan_trips):
        if index == 0:
            start_stop = stops[stops['stop_id'] == plan_trip.start_from_stop_id].iloc[0]

            response[0] = f'''<div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;"><img style="width: 25px;" src="{static('base_view/img/WALK.png')}"><span style="margin-left: 10px; text-align: left;">{start_location} -> {start_stop["stop_name"]}</span></div>'''

        if index == len(plan.plan_trips) - 1:
            goal_stop = stops[stops['stop_id'] == plan_trip.leave_at_stop_id].iloc[0]

            response[len(plan.plan_trips)+1] = f'''<div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;"><img style="width: 25px;" src="{static('base_view/img/WALK.png')}"><span style="margin-left: 10px; text-align: left;"> {goal_stop["stop_name"]} -> {goal_location} </span></div>'''


        departure_time = seconds_to_time(plan_trip.departure_time)
        arrival_time = seconds_to_time(plan_trip.arrival_time)
        if plan_trip.trip_id:
            trip = trips[trips['trip_id'] == plan_trip.trip_id].iloc[0]
            route = trip['route_id']
            direction = trip['trip_headsign']
            response[index + 1] = f'''<div style="display: flex; width: 90%; flex-direction: column; justify-content: center; margin: 10px 0;"><div style="display:flex; align-items: center; margin: 10px 0;"><img src="{static('base_view/img/BUS.svg')}" alt="bus icon"/><span style="margin-left: 10px;">{route} - {direction} ({departure_time} - {arrival_time})</span></div><div class="stops" style="font-size: 14px; text-align: left;">'''

            trip = trips[plan_trip.trip_id]
            trip_stops = [stops[stop_id] for stop_id in trip.stop_ids]
            in_our_trip_flag = False

            for stop in trip_stops:
                if stop.stop_id == plan_trip.start_from_stop_id:
                    in_our_trip_flag = True

                if stop.stop_id == plan_trip.leave_at_stop_id:
                    in_our_trip_flag = False

                if in_our_trip_flag:
                    stop_df = stops[stops['stop_id'] == stop.stop_id].iloc[0]
                    departure_time = "12:00"
                    response[index+1] += f'''{departure_time} {stop_df['stop_name']}<br>'''

        else:
            start_stop = stops[stops['stop_id'] == plan_trip.start_from_stop_id].iloc[0]
            goal_stop = stops[stops['stop_id'] == plan_trip.leave_at_stop_id].iloc[0]

            response[index + 1] = f'''<div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;"><img style="width: 25px;" src="{static('base_view/img/WALK.png')}"><span style="margin-left: 10px; text-align: left;"> {start_stop['stop_name']} -> {goal_stop['stop_name']}  ({departure_time} - {arrival_time})</span></div>'''

        response[index+1] += "</div></div>"


    return response