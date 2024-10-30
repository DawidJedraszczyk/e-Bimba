import numpy as np
from .utils import *


class Stop:
    def __init__(self, stop_id: int, stop_lat: float, stop_lon: float, stop_name: str, stop_code: str):
        self.stop_id = stop_id
        self.stop_name = stop_name
        self.stop_code = stop_code
        self.stop_lat = stop_lat
        self.stop_lon = stop_lon
        self.trips = dict()  # trip_id: (stop_sequence, departure_time_s, service_id)
        self.stops_within_walking_straight = dict()  # stop_id: walking_time_s
        self.stops_within_walking_manhattan = dict()  # stop_id: walking_time_s

    # this method is called multiple time in DataLoaderSingleton class, should be used for data structures initialization
    def add_trip(self, trip_id: str, stop_sequence: int, departure_time_s: int, service_id: int):
        # stop_sequence here is the index of this stop in the order of the trip
        self.trips[trip_id] = (stop_sequence, departure_time_s, service_id)

    """ tymczasowo, i chyba ostatcznie to nie będzie używane
    def prepare_sorted_trips(self):
        # FIXME - 24:30 should be before 00:10
        #Prepares added trips for use of 'constrained' `get_next_trips()`
        self.prepared_sorted_trips = np.array([
            trip_id for trip_id, _
            in sorted(self.trips.items(), key=lambda x: x[1][1])  # sorted by departure_time_s
        ])
    """

    def add_stop_within_walking_straight(
            self, stop_id: int, walking_time_s: int
    ):
        self.stops_within_walking_straight[stop_id] = walking_time_s

    def add_stop_within_walking_manhattan(
            self, stop_id: int, walking_time_s: int
    ):
        self.stops_within_walking_manhattan[stop_id] = walking_time_s

    def get_next_trips(
            self, start_time_s: int,
            within_time_s: int = 900,  # WITHIN_TIME_S,
            # for the best precisson this can be set to the time of walking from this stop to destination, but should never be more than 6
            min_trips: int = 10,  # MIN_TRIPS
            date_str: str = None,  # The date in 'YYYY-MM-DD'
            extended_timeframe_duration_s: int = 1800
            # The time in seconds for which the timeframe is extended to get more trips,
            # that is temporary solution and will be change if we decide to use destination walking time for within_time_s
    ) -> dict[int, (int, int)]:
        next_trips = dict()  # trip_id: (stop_index_in_sequence, departure_time_s, date_str)

        # TODO this can have better optmization.
        # within_time_s, min_trips, extended_timeframe_duration_s, should be kept outside as the parmeters of an algorithm

        today_service_id = get_date_service_id(date_str)
        yesterday_service_id = get_date_service_id(get_previous_day(date_str))
        tomorrow_service_id = get_date_service_id(get_next_day(date_str))

        timeframe_begin_s = start_time_s
        timeframe_end_s = start_time_s + within_time_s

        # first get all trips within specified time (within_time),
        # then, if needed, extend the time frame to get >= min_trips but for no longer than 5h
        # TODO eventually this 5h value used here should be no greater than a walking time to destination
        while len(
                next_trips) <= min_trips and timeframe_end_s - start_time_s <= 900:  # 15 min just for simplicity instead of 5h
            # if timeframe_begin_s != start_time_s:
            # print(f'{self.stop_id}: Extending timeframe to {seconds_to_time(timeframe_end_s)}, trips so far: {len(next_trips)}')
            # for the same callendar day
            for trip_id, (stop_sequence, departure_time_s, service_id) in self.trips.items():
                if timeframe_begin_s <= departure_time_s <= timeframe_end_s and service_id == today_service_id:
                    next_trips[trip_id] = (stop_sequence, departure_time_s, date_str)

            # for the next callendar day if needed
            if timeframe_end_s >= time_to_seconds('24:00:00'):
                for trip_id, (stop_sequence, departure_time_s, service_id) in self.trips.items():
                    if timeframe_begin_s - time_to_seconds(
                            '24:00:00') <= departure_time_s <= timeframe_end_s - time_to_seconds(
                            '24:00:00') and service_id == tomorrow_service_id:
                        next_trips[trip_id] = (stop_sequence, departure_time_s, get_next_day(date_str))

            # for the previous callendar day night busses where extended time format is used
            # CRITICAL ASSUMPTION for better pefrommance I assume that there are no night busses after 7:00
            if timeframe_begin_s <= time_to_seconds('7:00:00'):
                for trip_id, (stop_sequence, departure_time_s, service_id) in self.trips.items():
                    if timeframe_begin_s + time_to_seconds(
                            '24:00:00') <= departure_time_s <= timeframe_end_s + time_to_seconds(
                            '24:00:00') and service_id == yesterday_service_id:
                        next_trips[trip_id] = (stop_sequence, departure_time_s, get_previous_day(date_str))

            timeframe_end_s += extended_timeframe_duration_s
            timeframe_begin_s += extended_timeframe_duration_s

        return next_trips

    def __str__(self) -> str:
        return f'{self.stop_name} ({self.stop_code}, id={self.stop_id})'

    def cords_to_string(self) -> str:
        return f'(stop_id={self.stop_id}, stop_lat={self.stop_lat}, stop_lon={self.stop_lon})'