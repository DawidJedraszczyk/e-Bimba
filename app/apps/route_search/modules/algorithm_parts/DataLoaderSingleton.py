"""
import redis
import pickle
from ebus.settings import REDIS_HOST, REDIS_PORT"""
import pandas as pd
from time import time
from itertools import combinations
from haversine import haversine, Unit
import os
from pathlib import Path
from .utils import time_to_seconds, custom_print, manhattan_distance
from ebus.algorithm_settings import WALKING_SETTINGS
from .TimetableTrip import TimetableTrip
from .Stop import Stop

try:
    from django.conf import settings
except:
    class settings:
        BASE_DIR = str(Path(__file__).parents[4])


class BiDirectionalKeyDict(dict):
    """
    Dict that orders input key tuple
    regardless of the order of the keys
    Example:
    ('Politechnika', 'Rondo Kaponiera') is treated the same as ('Rondo Kaponiera', 'Politechnika')
    """

    def __setitem__(self, key, value):
        super().__setitem__(tuple(sorted(key)), value)

    def __getitem__(self, key):
        return super().__getitem__(tuple(sorted(key)))

    def __contains__(self, key):
        return super().__contains__(tuple(sorted(key)))


class DataLoaderSingleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DataLoaderSingleton, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.__dataframes = self.__load_GTFS_into_dataframes()
            self.__preprocess_time_format()
            self.__trips = self.__initialize_TimetableTrip()
            self.__stops = self.__initialize_Stops()
            self.__distances_straight = self.__compute_distances_straight()
            self.__distances_manhattan = self.__compute_distances_manhattan()
            self.__walking_times_straight = self.__compute_walking_times_straight()
            self.__walking_times_manhattan = self.__compute_walking_times_manhattan()

            self.__set_stops_within_walking_straight()
            self.__set_stops_within_walking_manhattan()

            self.initialized = True

    # Private methods that should be used only once, optimally when server starts

    def __load_GTFS_into_dataframes(self):
        t0 = time()
        data_folder_path = os.path.join(settings.BASE_DIR, "apps/route_search/modules/algorithm_parts/data/")
        data_file_format_suffix = ".txt"
        data_files = ["agency", "calendar", "feed_info", "routes", "shapes", "stop_times", "stops", "trips"]

        data_files_paths = [
            f'{data_folder_path}{data_file}{data_file_format_suffix}'
            for data_file in data_files
        ]

        dataframes = {
            data_file: pd.read_csv(data_file_path)
            for data_file, data_file_path in zip(data_files, data_files_paths)
        }
        dataframes['trips'].set_index('trip_id', inplace=True)
        dataframes['stops'].set_index('stop_id', inplace=True)
        custom_print(f'(loading gtfs - {time() - t0:.4f}s)', 'SETUP_TIMES')
        return dataframes

    def __preprocess_time_format(self):
        t0 = time()
        self.__dataframes['stop_times']['departure_time_s'] = \
            self.__dataframes['stop_times']['departure_time'].apply(time_to_seconds)
        self.__dataframes['stop_times']['arrival_time_s'] = \
            self.__dataframes['stop_times']['arrival_time'].apply(time_to_seconds)
        custom_print(f'(stop_times time_to_seconds() preprocessing - {time() - t0:.4f}s)', 'DATASTRUCTURES_INIT_TIMES')

    def __initialize_TimetableTrip(self):
        t0 = time()
        trips = {}
        for trip_id, trip_group in self.__dataframes['stop_times'].groupby('trip_id'):
            service_id = self.__dataframes['trips'].loc[trip_id, 'service_id']
            trips[trip_id] = TimetableTrip(trip_id=trip_id, trip_group=trip_group, service_id=service_id)
        custom_print(f'(load trips - {time() - t0:.4f}s)', 'DATASTRUCTURES_INIT_TIMES')
        return trips

    def __initialize_Stops(self):
        t0 = time()
        stops = {}
        for id, row in self.__dataframes['stops'].iterrows():
            stops[id] = Stop(
                stop_id=id,
                stop_lat=row['stop_lat'],
                stop_lon=row['stop_lon'],
                stop_name=row['stop_name'],
                stop_code=row['stop_code'],
            )
        custom_print(f'(load stops - {time() - t0:.4f}s)', 'DATASTRUCTURES_INIT_TIMES')

        # set trips in stops for easy access by algorithm
        t0 = time()
        for trip in self.__trips.values():

            for i in range(len(trip.stop_ids)):
                stops[trip.stop_ids[i]].add_trip(
                    trip_id=trip.trip_id,
                    stop_sequence=i,
                    departure_time_s=trip.departure_times_s[i],
                    service_id=trip.service_id
                )
        custom_print(f'(stops.set_trips - {time() - t0:.4f}s)', 'DATASTRUCTURES_INIT_TIMES')
        return stops

    def __compute_distances_straight(self):
        # distances in straight line between stops
        t0 = time()
        distances_straight = BiDirectionalKeyDict()  # (stop_id_1, stop_id_2): distance in straight line (m)
        # combinations(self.__stops.keys(), 2) - generates all possible pairs of 2 stops
        for stop_id_1, stop_id_2 in combinations(self.__stops.keys(), 2):
            # haversine - works like euclidean, but considers earth's curvature
            distances_straight[(stop_id_1, stop_id_2)] = haversine(
                (self.__stops[stop_id_1].stop_lat, self.__stops[stop_id_1].stop_lon),
                (self.__stops[stop_id_2].stop_lat, self.__stops[stop_id_2].stop_lon),
                unit=Unit.METERS
            )
        custom_print(f'(distances_straight - {time() - t0:.4f}s)', 'DATASTRUCTURES_INIT_TIMES')
        return distances_straight

    def __compute_distances_manhattan(self):
        t0 = time()
        distances_manhattan = BiDirectionalKeyDict()
        for stop_id_1, stop_id_2 in combinations(self.__stops.keys(), 2):
            distances_manhattan[(stop_id_1, stop_id_2)] = manhattan_distance(
                self.__stops[stop_id_1].stop_lat, self.__stops[stop_id_1].stop_lon,
                self.__stops[stop_id_2].stop_lat, self.__stops[stop_id_2].stop_lon
            )
        custom_print(f'(distances_manhattan - {time() - t0:.4f}s)', 'DATASTRUCTURES_INIT_TIMES')
        return distances_manhattan

    def __compute_walking_times_straight(self):
        # walking times (straight line)
        t0 = time()
        walking_times_straight = BiDirectionalKeyDict()
        for stop_ids_key, distance in self.__distances_straight.items():
            walking_times_straight[stop_ids_key] = distance / WALKING_SETTINGS['PACE']
        custom_print(f'(walking_times_straight - {time() - t0:.4f}s)', 'DATASTRUCTURES_INIT_TIMES')
        return walking_times_straight

    def __compute_walking_times_manhattan(self):
        t0 = time()
        walking_times_manhattan = BiDirectionalKeyDict()
        for stop_ids_key, distance in self.__distances_manhattan.items():
            walking_times_manhattan[stop_ids_key] = distance / WALKING_SETTINGS['PACE']
        custom_print(f'(walking_times_manhattan - {time() - t0:.4f}s)', 'DATASTRUCTURES_INIT_TIMES')
        return walking_times_manhattan

    def __set_stops_within_walking_straight(self):
        t0 = time()
        for (stop_id_1, stop_id_2), walking_time in self.__walking_times_straight.items():
            if walking_time > WALKING_SETTINGS['TIME_WITHIN_WALKING']:
                continue
            self.__stops[stop_id_1].add_stop_within_walking_straight(stop_id=stop_id_2, walking_time_s=walking_time)
            self.__stops[stop_id_2].add_stop_within_walking_straight(stop_id=stop_id_1, walking_time_s=walking_time)
        custom_print(f'(stops_within_walking_straight - {time() - t0:.4f}s)', 'DATASTRUCTURES_INIT_TIMES')

    def __set_stops_within_walking_manhattan(self):
        t0 = time()
        for (stop_id_1, stop_id_2), walking_time in self.__walking_times_manhattan.items():
            if walking_time > WALKING_SETTINGS['TIME_WITHIN_WALKING']:
                continue
            self.__stops[stop_id_1].add_stop_within_walking_manhattan(stop_id=stop_id_2, walking_time_s=walking_time)
            self.__stops[stop_id_2].add_stop_within_walking_manhattan(stop_id=stop_id_1, walking_time_s=walking_time)
        custom_print(f'(stops_within_walking_manhattan - {time() - t0:.4f}s)', 'DATASTRUCTURES_INIT_TIMES')

    # Public methods

    def get_stops(self):
        return self.__stops

    def get_stops_df(self):
        return self.__dataframes['stops']

    def get_trips(self):
        return self.__trips

    def get_trips_df(self):
        return self.__dataframes['trips']

    def get_routes_df(self):
        return self.__dataframes['routes']

    # this getters are not reqired by the algorithm, but needed for route drawing

    def get_shapes_df(self):
        return self.__dataframes['shapes']

initialized_dataloader_singleton = DataLoaderSingleton()
