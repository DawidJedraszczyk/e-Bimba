import datetime
from haversine import haversine, Unit
from ebus.algorithm_settings import PRINTING_SETTINGS


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


def plans_to_string(found_plans, data):
    result = ""
    for i, plan in enumerate(found_plans):
        result += '\t-----------------\n'
        result += f'\tPlan {i}\n'
        result += "\t" + plan.format(data).replace("\n", "\n\t") + "\n"
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
