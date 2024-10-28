import datetime
from haversine import haversine, Unit
from ebus.algorithm_settings import PRINTING_SETTINGS
from django.templatetags.static import static
import pandas as pd


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

def get_lat_lon_sets(shapes_df, shape_id):
    shapes = shapes_df[shapes_df['shape_id'] == shape_id]

    lat_lon_sets = [(row['shape_pt_lat'], row['shape_pt_lon']) for _, row in shapes.iterrows()]

    return lat_lon_sets

def get_closest_shape_point(stop_lat, stop_lon, shape_points):
    closest_point = None
    closest_distance = float('inf')

    for shape_point in shape_points:
        point_lat, point_lon = shape_point
        distance = haversine((stop_lat, stop_lon), (point_lat, point_lon), Unit.METERS)

        if distance < closest_distance:
            closest_distance = distance
            closest_point = shape_point

    return closest_point