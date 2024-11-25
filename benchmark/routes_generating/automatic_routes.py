from itertools import product

from routes_generating.resources import locations_dict, times, dates, restricted_locations_dict
from components.SampleRoute import SampleRoute

def get_all_automatic_sample_routes():
    sample_routes = []
    for start, destination, time, date in product(locations_dict.keys(), locations_dict.keys(), times, dates):
        if start != destination:
            sample_routes.append(SampleRoute(start, destination, time, date=date))
    return sample_routes

def get_small_instance_automatic_sample_routes():
    sample_routes = []
    for start, destination in product(restricted_locations_dict.keys(), restricted_locations_dict.keys()):
        if start != destination:
            sample_routes.append(SampleRoute(start, destination, '7:30:00', date='2024-09-05'))
    return sample_routes
