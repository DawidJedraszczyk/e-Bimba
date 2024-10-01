import pandas as pd
import numpy as np
from time import time
from itertools import combinations
from haversine import haversine, Unit
import heapq
import csv
import os
from django.templatetags.static import static

from ebus.settings import BASE_DIR
from ebus.algorithm_settings import *




def time_to_seconds(time_str: str) -> int:
    """Maps time from HH:MM:SS format to total no. of seconds"""
    hms = [int(i) for i in time_str.split(':')]
    return hms[0]*3600 + hms[1]*60 + hms[2]

def seconds_to_time(time_seconds) -> str:
    """Maps time from total no. of seconds to HH:MM:SS format"""
    time_seconds = int(time_seconds)
    hours = time_seconds // 3600
    time_seconds %= 3600
    minutes = time_seconds // 60
    time_seconds %= 60
    return f"{hours:02}:{minutes:02}:{time_seconds:02}"

def is_earlier_hour(fastest_known_time, arrival_time): #given in seconds
    """Return True if time1 is later than time2."""
    fastest_known_time_standardized = fastest_known_time % (86400)
    arrival_time_standardized = arrival_time % (86400)
    difference = fastest_known_time_standardized - arrival_time_standardized
    if difference > 0 and difference < 43200:
        return True
    else:
        return False

class Trip:
    def __init__(self, trip_id: str, trip_group):
        self.trip_id = trip_id
        self.stop_ids = np.array(trip_group[
                                     'stop_id'])  # simplicity, assume in order (stop_sequence) WHICH IS THE CASE (but implement check in app?)
        self.arrival_times_s = np.array(trip_group['arrival_time_s'])
        self.departure_times_s = np.array(trip_group['departure_time_s'])

        # route_id not needed for algo; can be done in "mapping to app needs"

    def __str__(self):
        return f"Trip(\ntrip_id={self.trip_id},\nstop_ids={self.stop_ids},\narrival_times_seconds={self.arrival_times_s},\ndeparture_times_seconds={self.departure_times_s},\n)"


# default values governing logic of which next trips are chosen
# WITHIN_TIME_S = time_to_seconds('00:15:00'),
# MIN_TRIPS = 10
# FIXME - providing the above like this doesn't work?

# for planning trips that span into next day (assuming the same schedule)
# one_day_offset_s = time_to_seconds('24:00:00')

class Stop:
    def __init__(self, stop_id: int, stop_lat: float, stop_lon: float):
        self.stop_id = stop_id
        self.stop_lat = stop_lat
        self.stop_lon = stop_lon
        self.trips = dict()  # trip_id: (stop_sequence, departure_time_s)
        # TODO - use one/other/both?
        # TODO - "within X time, but at least N min"??
        self.stops_within_walking_straight = dict()  # stop_id: walking_time_s
        self.stops_within_walking_manhattan = dict()  # stop_id: walking_time_s

    def add_trip(self, trip_id: str, stop_sequence: int, departure_time_s: int):
        self.trips[trip_id] = (stop_sequence, departure_time_s)

    def prepare_sorted_trips(self):
        """Prepares added trips for use of 'constrained' `get_next_trips()`"""
        self.prepared_sorted_trips = np.array([
            trip_id for trip_id, _
            in sorted(self.trips.items(), key=lambda x: x[1][1])  # sorted by departure_time_s
        ])

    def add_stop_within_walking_straight(
            self, stop_id: int, walking_time_s: int
    ):
        self.stops_within_walking_straight[stop_id] = walking_time_s

    def add_stop_within_walking_manhattan(
            self, stop_id: int, walking_time_s: int
    ):
        self.stops_within_walking_manhattan[stop_id] = walking_time_s

    def get_next_trips(
            self, time_s: int,
            within_time: int = 900,
            # WITHIN_TIME_S, for the best precisson this can be set to the time of walking from this stop to destination, but should never be more than 6
            min_trips: int = 10  # MIN_TRIPS
    ) -> dict[int, (int, int)]:
        next_trips = dict()  # trip_id: (stop_sequence, departure_time_s)

        # TODO - "no way" same trip_id used again (just take into account +1D offset in algo + output mapping)
        # 2500, 1200(+1D)

        # first get all trips within specified time
        max_time = time_s + within_time
        for trip_id, (stop_sequence, departure_time_s) in self.trips.items():
            # dla tego samego dnia
            if time_s <= departure_time_s <= max_time:
                next_trips[trip_id] = (stop_sequence, departure_time_s)
                """     
        if max_time >= time_to_seconds('24:00:00'):
            for trip_id, (stop_sequence, departure_time_s) in self.trips.items():
            # dla nastepnego dnia
                if time_s-time_to_seconds('24:00:00') <= departure_time_s <= max_time-time_to_seconds('24:00:00'):
                    next_trips[trip_id] = (stop_sequence, departure_time_s)

        # najpóźniej kiedy mogłyby jeżdzić nocne autobusy
        if max_time <= time_to_seconds('10:00:00'):
            for trip_id, (stop_sequence, departure_time_s) in self.trips.items():
            # dla poprzedniego dnia
                if time_s+time_to_seconds('24:00:00') <= departure_time_s <= max_time+time_to_seconds('24:00:00'):
                    next_trips[trip_id] = (stop_sequence, departure_time_s)
"""
            # it's possible that plan will span to next day

            # FIXME - just this is insufficient; it's only for one step of the algorithm,
            # but then it doesn't distinguish time
            # SOME WORKAROUND - "artificial" trip? (e.g. '-1d' suffix?)
            # next_day_departure_time = departure_time_s + one_day_offset_s
            # if next_day_departure_time <= max_time:
            # next_trips[trip_id] = (stop_sequence, next_day_departure_time)
        if len(next_trips) >= min_trips:
            return next_trips

        # if that's not enough trips, add next ones that are not within specified time
        for trip_id in self.prepared_sorted_trips:
            # TODO - "loop" these trips to keep adding until sufficient min reached?
            # FIXME - trips spanning to next day
            if trip_id not in next_trips:
                stop_sequence, departure_time_s = self.trips[trip_id]
                if time_s <= departure_time_s:
                    next_trips[trip_id] = (stop_sequence, departure_time_s)
                    if len(next_trips) == min_trips:
                        return next_trips

        # safeguard against insufficient stops
        return next_trips

    #         "        return {\n",
    #     "            trip_id: (stop_sequence, departure_time)\n",
    #     "            for trip_id, (stop_sequence, departure_time) in self.trips.items()\n",
    #     "            if time_s <= departure_time\n",
    #     "        }\n",

    def __str__(self) -> str:
        return f'Stop(stop_id={self.stop_id}, stop_lat={self.stop_lat}, stop_lon={self.stop_lon})'


class BiDirectionalKeyDict(dict):
    """Dict that orders input key tuple"""

    def __setitem__(self, key, value):
        super().__setitem__(tuple(sorted(key)), value)

    def __getitem__(self, key):
        return super().__getitem__(tuple(sorted(key)))

    def __contains__(self, key):
        return super().__contains__(tuple(sorted(key)))

def manhattan_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> float:
    """Calculates Manhattan (city) distance between two points"""
    distance_across_latitude  = haversine((lat1, lon1), (lat2, lon1), unit=Unit.METERS)
    distance_across_longitude = haversine((lat1, lon1), (lat1, lon2), unit=Unit.METERS)
    return distance_across_latitude + distance_across_longitude

def get_start_walking_times(distance_metric, START):
    if distance_metric == 'straight':
        start_walking_times = {
            stop.stop_id: haversine(
                (stop.stop_lat, stop.stop_lon), START,
                unit=Unit.METERS
            ) / WALKING_SETTINGS['PACE']
            for stop in stops.values()
        }
    elif distance_metric == 'manhattan':
        start_walking_times = {
        stop.stop_id: manhattan_distance(
            stop.stop_lat, stop.stop_lon,
            START[0], START[1]
        ) / WALKING_SETTINGS['PACE']
        for stop in stops.values()
        }
    else:
        raise ValueError(f'Unknown distance metric: {distance_metric}')
    #print(f'(start_walking_times_straight - {time()-t0:.4f}s)')
    return start_walking_times

def get_start_within_walking(distance_metric, START):
    # todo - may need to specify incremental increase in case no route found?
    #   or similar "at least X"? or somehow "without explicit"?
    start_walking_times = get_start_walking_times(distance_metric, START)
    start_within_walking = {
        stop_id: walking_time
        for stop_id, walking_time in start_walking_times.items()
        if walking_time <= WALKING_SETTINGS['TIME_WITHIN_WALKING']
    }
    #print(f'(start_within_walking - {time()-t0:.4f}s)')
    return start_within_walking


def get_destination_walking_times(distance_metric, DESTINATION):
    if distance_metric == 'straight':
        destination_walking_times = {
            stop.stop_id: haversine(
                (stop.stop_lat, stop.stop_lon), DESTINATION,
                unit=Unit.METERS
            ) / WALKING_SETTINGS['PACE']
            for stop in stops.values()
        }
    elif distance_metric == 'manhattan':
        destination_walking_times = {
        stop.stop_id: manhattan_distance(
            stop.stop_lat, stop.stop_lon,
            DESTINATION[0], DESTINATION[1]
        ) / WALKING_SETTINGS['PACE']
        for stop in stops.values()
        }
    else:
        raise ValueError(f'Unknown distance metric: {distance_metric}')
    #print(f'(destination_walking_times_straight - {time()-t0:.4f}s)')
    return destination_walking_times

# FIXME - this may be overestimating (especially in Manhattan) -> potential problems
#   BUT note that this may work in practice anyways



# heuristic = time with tram avg speed to dest + assumed walking time constant
def get_destination_heurisitc_time(distance_metric, DESTINATION):
    if distance_metric == 'straight':
        heuristic_times = {
            stop.stop_id: haversine(
                (stop.stop_lat, stop.stop_lon), DESTINATION,
                unit=Unit.METERS
            ) / TRAM_SETTINGS['AVG_SPEED'] + WALKING_SETTINGS['ALWAYS_WALKING_TIME_CONSTANT']
            for stop in stops.values()
        }
    elif distance_metric == 'manhattan':
        heuristic_times = {
            stop.stop_id: manhattan_distance(
                stop.stop_lat, stop.stop_lon,
                DESTINATION[0], DESTINATION[1]
            ) / TRAM_SETTINGS['AVG_SPEED'] + WALKING_SETTINGS['ALWAYS_WALKING_TIME_CONSTANT']
            for stop in stops.values()
        }
    else:
        raise ValueError(f'Unknown distance metric: {distance_metric}')
    return heuristic_times


def trip_to_string(plan_trip):
    stop_from_df = dataframes['stops'][dataframes['stops']['stop_id'] == plan_trip.start_from_stop_id].iloc[0]
    trip_str = f"\t\tget from {stop_from_df['stop_code']}: {stop_from_df['stop_name']} (stop_id={plan_trip.start_from_stop_id})\n"
    if plan_trip.type == 'WALK':
        trip_str += f"\t\t\tBY FOOT to {plan_trip.leave_at_stop_id} (time: {seconds_to_time(plan_trip.departure_time)}-{seconds_to_time(plan_trip.arrival_time)})\n"
    else:
        trip_from_df = dataframes['trips'][dataframes['trips']['trip_id'] == plan_trip.trip_id].iloc[0]
        trip_str += f"\t\t\tusing {trip_from_df['route_id']} ({plan_trip.trip_id}), at times: {seconds_to_time(plan_trip.departure_time)}-{seconds_to_time(plan_trip.arrival_time)}\n"
    stop_to_df = dataframes['stops'][dataframes['stops']['stop_id'] == plan_trip.leave_at_stop_id].iloc[0]
    trip_str += f"\t\tto {stop_to_df['stop_code']}: {stop_to_df['stop_name']} (stop_id={plan_trip.leave_at_stop_id})"
    return trip_str

def print_trip(plan_trip):
    print(trip_to_string(plan_trip))
    """
    stop_from_df = dataframes['stops'][dataframes['stops']['stop_id'] == plan_trip.start_from_stop_id].iloc[0]
    print(f"\t\tget from {stop_from_df['stop_code']}: {stop_from_df['stop_name']} (stop_id={plan_trip.start_from_stop_id})")
    if plan_trip.type == 'WALK':
        print(f"\t\t\tBY FOOT to {plan_trip.leave_at_stop_id} (time: {seconds_to_time(plan_trip.departure_time)}-{seconds_to_time(plan_trip.arrival_time)})")
    else:
        trip_from_df = dataframes['trips'][dataframes['trips']['trip_id'] == plan_trip.trip_id].iloc[0]            
        print(f"\t\t\tusing {trip_from_df['route_id']} ({plan_trip.trip_id}), at times: {seconds_to_time(plan_trip.departure_time)}-{seconds_to_time(plan_trip.arrival_time)}")
    stop_to_df = dataframes['stops'][dataframes['stops']['stop_id'] == plan_trip.leave_at_stop_id].iloc[0]
    print(f"\t\tto {stop_to_df['stop_code']}: {stop_to_df['stop_name']} (stop_id={plan_trip.leave_at_stop_id})")
    """
def plans_to_string(found_plans):
    result = ""
    for i, plan in enumerate(found_plans):
        result += '\t-----------------\n'
        result += f'\tPlan {i}\n'
        starting_stop_id = plan.current_stop_id if len(plan.plan_trips) == 0 else plan.plan_trips[0].start_from_stop_id
        stop_from_df = dataframes['stops'][dataframes['stops']['stop_id'] == starting_stop_id].iloc[0]
        result += f"\tstart at: {stop_from_df['stop_code']}: {stop_from_df['stop_name']} (stop_id={starting_stop_id}), time: {seconds_to_time(plan.start_time)}\n"
        for plan_trip in plan.plan_trips:
            result += trip_to_string(plan_trip) + "\n"
        result += f"\treach destination at {seconds_to_time(plan.time_at_destination)}\n"
    return result

def print_plans(found_plans):
    print(plans_to_string(found_plans))
    """
    for i, plan in enumerate(found_plans):
        print('\t-----------------')
        print(f'\tPlan {i}')
        starting_stop_id = plan.current_stop_id if len(plan.plan_trips) == 0 else plan.plan_trips[0].start_from_stop_id
        stop_from_df = dataframes['stops'][dataframes['stops']['stop_id'] == starting_stop_id].iloc[0]
        print(f"\tstart at: {stop_from_df['stop_code']}: {stop_from_df['stop_name']} (stop_id={starting_stop_id}), time: {seconds_to_time(plan.start_time)}")
        for plan_trip in plan.plan_trips:
            print_trip(plan_trip)
        print(f"\treach destination at {seconds_to_time(plan.time_at_destination)}")"""


def plans_to_html(found_plans):
    response = {}

    for index, plan in enumerate(found_plans):
        communication = []
        start_time = None
        destination_time = seconds_to_time(plan.time_at_destination)

        for plan_trip in plan.plan_trips:
            if not plan_trip.type == 'WALK':
                trip_from_df = dataframes['trips'][dataframes['trips']['trip_id'] == plan_trip.trip_id].iloc[0]
                if not start_time:
                    start_time = seconds_to_time(plan_trip.departure_time)

                communication.append(trip_from_df['route_id'])


        communication_content = ''
        for travel_option in communication:
            communication_content += f'''<div style="padding: 5px; display: flex; flex-direction: column; justify-content: center; align-items: center;"><img style="height: 23px; width: 23px; margin-bottom: 5px;" src="{static('base_view/img/BUS.svg')}">{str(travel_option)}</div>'''

        prepared_solution = {
            'div': f'''<div style="display:none"></div>
                       <div id="{index}" class="solution" style="width: 99%; border: solid 1px white; padding: 20px 0px; border-radius: 5px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                           <div style="font-size: 25px; margin-left: 5px;">{start_time}</div>
                           <div style="display: flex;">{communication_content}</div>
                           <div style="font-size: 25px; margin-right: 5px;">{destination_time}</div>
                       </div>
                    '''
        }
        response[str(index)] = prepared_solution
    return response



class PlanTrip:
    def __init__(
            self,
            start_from_stop_id, departure_time,
            leave_at_stop_id, arrival_time, type, trip_id=None
    ):
        self.type = type  # bus/walking/train/bike/car
        # if it is bus trip,
        if type == 'bus' and trip_id is None:
            raise ValueError("trip_id must be provided for bus trips")
        self.trip_id = trip_id
        self.departure_time = departure_time
        self.arrival_time = arrival_time
        # Those two are also needed to be modified when we start to consider bicycles,
        # because the trips may no longer start or finish at the bus stops
        self.start_from_stop_id = start_from_stop_id
        self.leave_at_stop_id = leave_at_stop_id

    def __str__(self):
        return f"PlanTrip({';'.join([self.type, self.trip_id, self.start_from_stop_id, self.departure_time, self.leave_at_stop_id, self.arrival_time])})"

    def __repr__(self):
        return f"PlanTrip({';'.join(map(str, [self.type, self.trip_id, self.start_from_stop_id, self.departure_time, self.leave_at_stop_id, self.arrival_time]))})"


class Plan():
    """
    `starting_stop_id` is used for initialization of A*                           \n
    - it is the stop_id's of stops within walking distance of start location      \n
    - should be `None` in further usage after initialization, when instead, we're
      building Plans by extending current ones                                    \n

    `plan_trips` is used after initialization of A*                               \n
    - it is the `PlanTrip`s explored between start and destination                \n
    - should be `None` in initialization, when we're just starting to build Plans

    in Java, we'd do separate constructors;                                       \n
    Python requires workarounds within single one
    """

    def __init__(
            self,
            start_walking_times,
            destination_walking_times,
            heuristic_times,
            start_time,  # start time of the plan (used only for initialization)
            starting_stop_id: int = None,
            plan_trips: list[PlanTrip] = None,
    ):
        self.start_time = start_time
        if starting_stop_id is None and plan_trips is None:
            raise Exception('either starting_stop_id or plan_trips must be specified')

        if starting_stop_id is not None:
            # initialization
            self.plan_trips = list()
            self.used_trips = set()
            self.used_stops = set()
            self.current_stop_id = starting_stop_id
            self.current_time = self.start_time + start_walking_times[starting_stop_id]
            self.time_at_destination = self.current_time + destination_walking_times[starting_stop_id]
            self.heuristic_time_at_destination = self.current_time + heuristic_times[starting_stop_id]

        if plan_trips is not None:
            # extended plan
            self.plan_trips = plan_trips
            self.used_trips = {plan_trip.trip_id for plan_trip in plan_trips}
            self.used_stops = {plan_trip.start_from_stop_id for plan_trip in plan_trips}
            last_plan_trip = plan_trips[-1]
            self.current_stop_id = last_plan_trip.leave_at_stop_id
            self.current_time = last_plan_trip.arrival_time
            self.time_at_destination = last_plan_trip.arrival_time + destination_walking_times[
                last_plan_trip.leave_at_stop_id]
            self.heuristic_time_at_destination = last_plan_trip.arrival_time + heuristic_times[
                last_plan_trip.leave_at_stop_id]

        # simple flag that distinguishes between potential terminal plans from ones in heuristic stage
        self.is_terminal = False

    def set_as_terminal(self):
        self.is_terminal = True

    def get_informed_time_at_destination(self):
        """Gets time at destination, taking into account if plan is terminal"""
        return self.time_at_destination if self.is_terminal else self.heuristic_time_at_destination

    def __repr__(self):
        return f"Plan({';'.join(map(str, [self.plan_trips, self.used_trips, self.current_stop_id, self.current_time, self.time_at_destination]))})"

    def __lt__(self, other):
        return self.get_informed_time_at_destination() < other.get_informed_time_at_destination()

    def __le__(self, other):
        return self.get_informed_time_at_destination() <= other.get_informed_time_at_destination()

    def __eq__(self, other):
        return self.get_informed_time_at_destination() == other.get_informed_time_at_destination()

    def __ne__(self, other):
        return self.get_informed_time_at_destination() != other.get_informed_time_at_destination()

    def __gt__(self, other):
        return self.get_informed_time_at_destination() > other.get_informed_time_at_destination()

    def __ge__(self, other):
        return self.get_informed_time_at_destination() >= other.get_informed_time_at_destination()


class AStarPlanner():
    def __init__(self, start_time, START, DESTINATION, distance_metric,
                 waiting_time_constant=time_to_seconds('00:03:00')):
        # FIXME - plan for "just walk" (special case Plan-like object with sufficient methods? interface?)
        # would prefer ugly if statement at each recursion
        self.start_time = start_time
        self.start = START
        self.destination = DESTINATION
        self.waiting_time_constant = waiting_time_constant
        self.start_walking_times = get_start_walking_times(distance_metric, START)
        self.destination_walking_times = get_destination_walking_times(distance_metric, DESTINATION)
        self.heuristic_times = get_destination_heurisitc_time(distance_metric, DESTINATION)
        self.start_within_walking = get_start_within_walking(distance_metric, START)
        self.plans_queue = []
        for stop_id in self.start_within_walking.keys():
            plan = Plan(self.start_walking_times, self.destination_walking_times, self.heuristic_times, self.start_time,
                        starting_stop_id=stop_id)
            heapq.heappush(self.plans_queue, plan)
        self.found_plans = list()
        self.iterations = 0

    def find_next_plan(self):
        visited_stops = set()
        while len(self.plans_queue) != 0:
            self.iterations += 1
            # print('iteration', self.iterations)

            if not self.plans_queue:
                raise Exception('no more plans')

            # remove fastest known plan yet from queue
            plan_accepted = False
            while not plan_accepted:
                fastest_known_plan = heapq.heappop(self.plans_queue)
                # if this it True, it means that:
                # - heuristic doesn't point at anything potentially better
                # - among terminal plans in the queue, this is the fastest
                if fastest_known_plan.is_terminal:
                    self.found_plans.append(fastest_known_plan)
                    #print(self.iterations)
                    return fastest_known_plan
                if len(fastest_known_plan.plan_trips) == 0:
                    plan_accepted = True
                    continue
                last_stop_id = fastest_known_plan.plan_trips[-1].leave_at_stop_id
                if last_stop_id not in visited_stops:
                    plan_accepted = True
                    visited_stops.add(last_stop_id)

            # if len(fastest_known_plan.plan_trips) > 0:
            #   print_trip(fastest_known_plan.plan_trips[-1])

            # make this plan potential subject for terminal
            # (it was the best option so far and if remains so after we consider its
            # walking distance directly, it's good enough to be considered best result)
            fastest_known_plan.set_as_terminal()
            heapq.heappush(self.plans_queue, fastest_known_plan)

            # try extending queue with **fastest** ways to **all** reachable stops
            # from stop we're currently at after following fastest known plan yet
            current_stop = stops[fastest_known_plan.current_stop_id]
            fastest_ways = dict()  # stop_id: (trip_id, departure_time, arrival_time, type)
            ## factor in trips from this stop directly
            available_trips = current_stop.get_next_trips(
                time_s=fastest_known_plan.current_time + self.waiting_time_constant)
            for trip_id, (stop_sequence, departure_time) in available_trips.items():
                if trip_id in fastest_known_plan.used_trips:
                    continue  # covered in other plans, would be duplication
                trip = trips[trip_id]
                for i in range(stop_sequence + 1, len(trip.stop_ids)):
                    stop_id, arrival_time = trip.stop_ids[i], trip.arrival_times_s[i]
                    # WARNING - if the arrival is already on the next day, it will be wrong
                    # if stop_id not in fastest_ways.keys() or fastest_ways[stop_id][2] > arrival_time:
                    if stop_id not in fastest_ways.keys() or is_earlier_hour(fastest_ways[stop_id][2], arrival_time):
                        # actually it is sometimes a tram
                        fastest_ways[stop_id] = (trip_id, departure_time, arrival_time, 'BUS')
            ## factor in stops within walking distance

            for stop_id, walking_time in current_stop.stops_within_walking_straight.items():
                # TODO - get exact walking time
                # print(stop_id)
                # print(fastest_known_plan.used_stops)
                if stop_id not in fastest_known_plan.used_stops:
                    time_at_stop = fastest_known_plan.current_time + walking_time + WALKING_SETTINGS['ALWAYS_WALKING_TIME_CONSTANT']
                    # if stop_id not in fastest_ways.keys() or fastest_ways[stop_id][2] > arrival_time:
                    if stop_id not in fastest_ways.keys() or is_earlier_hour(fastest_ways[stop_id][2], arrival_time):
                        fastest_ways[stop_id] = (None, fastest_known_plan.current_time, time_at_stop, 'WALK')
                    # else:
                    # print('STOP ALREADY DISCOVERED, with faster time!')
                # else:
                # print('STOP ALREADY USED!')
            ## create extended plans and add them to the queue
            for stop_id, (trip_id, departure_time, arrival_time, type) in fastest_ways.items():
                # print('stop id:', current_stop.stop_id)
                extending_plan_trip = PlanTrip(
                    trip_id=trip_id,
                    start_from_stop_id=current_stop.stop_id,
                    departure_time=departure_time,
                    leave_at_stop_id=stop_id,
                    arrival_time=arrival_time,
                    type=type
                )
                extended_plan = Plan(self.start_walking_times,
                                     self.destination_walking_times,
                                     self.heuristic_times,
                                     self.start_time,
                                     plan_trips=fastest_known_plan.plan_trips + [extending_plan_trip])
                heapq.heappush(self.plans_queue, extended_plan)


def get_lat_lon_sets(shape_id):
    shapes = dataframes['shapes'][dataframes['shapes']['shape_id'] == shape_id]

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

    plan = astarplaner.found_plans[plan_num]


    for index, plan_trip in enumerate(plan.plan_trips):
        if index == 0:
            start_stop = dataframes['stops'][dataframes['stops']['stop_id'] == plan_trip.start_from_stop_id].iloc[0]
            response[0] = [astarplaner.start, (start_stop.stop_lat, start_stop.stop_lon)]

        if index == len(plan.plan_trips) - 1:
            goal_stop = dataframes['stops'][dataframes['stops']['stop_id'] == plan_trip.leave_at_stop_id].iloc[0]
            response[len(plan.plan_trips)+1] = [(goal_stop.stop_lat, goal_stop.stop_lon), astarplaner.destination]


        response[index+1] = []
        sequence_numbers = []

        if plan_trip.trip_id:
            trip = trips[plan_trip.trip_id]
            shape_id = int(dataframes['trips'][dataframes['trips']['trip_id'] == plan_trip.trip_id].iloc[0].shape_id)
            lat_lon_sets = get_lat_lon_sets(shape_id)
            trip_stops = [stops[stop_id] for stop_id in trip.stop_ids]


            for stop in trip_stops:
                if stop.stop_id == plan_trip.start_from_stop_id or stop.stop_id == plan_trip.leave_at_stop_id:

                    closest_point = find_closest_shape_point(stop.stop_lat, stop.stop_lon, lat_lon_sets)

                    closest_lat, closest_lon = closest_point  # Tuple unpacking should match the lat-lon order

                    filtered_shape = dataframes['shapes'][
                        (dataframes['shapes']['shape_id'] == shape_id) &
                        (dataframes['shapes']['shape_pt_lat'] == closest_lat) &
                        (dataframes['shapes']['shape_pt_lon'] == closest_lon)
                    ]

                    if not filtered_shape.empty:
                        seq_num = int(filtered_shape['shape_pt_sequence'].iloc[0])
                        sequence_numbers.append(seq_num)

            if sequence_numbers:
                min_seq_num = min(sequence_numbers)
                max_seq_num = max(sequence_numbers)

                matching_shapes = dataframes['shapes'][
                    (dataframes['shapes']['shape_id'] == shape_id) &
                    (dataframes['shapes']['shape_pt_sequence'] >= min_seq_num) &
                    (dataframes['shapes']['shape_pt_sequence'] <= max_seq_num)
                ]

                lat_lon_pairs = list(zip(matching_shapes['shape_pt_lat'], matching_shapes['shape_pt_lon']))

                response[index+1] = lat_lon_pairs

        else:
            start_stop = dataframes['stops'][dataframes['stops']['stop_id'] == plan_trip.start_from_stop_id].iloc[0]
            goal_stop = dataframes['stops'][dataframes['stops']['stop_id'] == plan_trip.leave_at_stop_id].iloc[0]

            response[index+1] = [(start_stop.stop_lat, start_stop.stop_lon), (goal_stop.stop_lat, goal_stop.stop_lon)]

    return response

import redis
import pickle
from ebus.settings import REDIS_HOST, REDIS_PORT

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

CACHE_KEY = 'processed_data'
def load_data_from_cache():
    cached_data = r.get(CACHE_KEY)
    if cached_data:
        return pickle.loads(cached_data)
    return None

def save_data_to_cache(stops, trips, walking_times_straight, walking_times_manhattan):
    data = pickle.dumps((stops, trips, walking_times_straight, walking_times_manhattan))
    r.set(CACHE_KEY, data)

data_folder_path = os.path.join(BASE_DIR, "apps/route_search/modules/algorithm/data/")
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

def process_data():
    dataframes['stop_times']['departure_time_s'] = dataframes['stop_times']['departure_time'].apply(time_to_seconds)
    dataframes['stop_times']['arrival_time_s'] = dataframes['stop_times']['arrival_time'].apply(time_to_seconds)

    trips = {
        trip_id: Trip(trip_id=trip_id, trip_group=trip_group)
        for trip_id, trip_group in dataframes['stop_times'].groupby('trip_id')
    }

    stops = {
        row['stop_id']: Stop(
            stop_id=row['stop_id'],
            stop_lat=row['stop_lat'],
            stop_lon=row['stop_lon']
        )
        for _, row in dataframes['stops'].iterrows()
    }

    for trip in trips.values():
        for i in range(len(trip.stop_ids)):
            stops[trip.stop_ids[i]].add_trip(
                trip_id=trip.trip_id,
                stop_sequence=i,
                departure_time_s=trip.departure_times_s[i]
            )

    for stop_id in stops.keys():
        stops[stop_id].prepare_sorted_trips()

    distances_straight = BiDirectionalKeyDict()
    for stop_id_1, stop_id_2 in combinations(stops.keys(), 2):
        distances_straight[(stop_id_1, stop_id_2)] = haversine(
            (stops[stop_id_1].stop_lat, stops[stop_id_1].stop_lon),
            (stops[stop_id_2].stop_lat, stops[stop_id_2].stop_lon),
            unit=Unit.METERS
        )

    distances_manhattan = BiDirectionalKeyDict()
    for stop_id_1, stop_id_2 in combinations(stops.keys(), 2):
        distances_manhattan[(stop_id_1, stop_id_2)] = manhattan_distance(
            stops[stop_id_1].stop_lat, stops[stop_id_1].stop_lon,
            stops[stop_id_2].stop_lat, stops[stop_id_2].stop_lon
        )

    walking_times_straight = BiDirectionalKeyDict()
    for stop_ids_key, distance in distances_straight.items():
        walking_times_straight[stop_ids_key] = distance / WALKING_SETTINGS['PACE']

    walking_times_manhattan = BiDirectionalKeyDict()
    for stop_ids_key, distance in distances_manhattan.items():
        walking_times_manhattan[stop_ids_key] = distance / WALKING_SETTINGS['PACE']

    for (stop_id_1, stop_id_2), walking_time in walking_times_straight.items():
        if walking_time > WALKING_SETTINGS['TIME_WITHIN_WALKING']:
            continue
        stops[stop_id_1].add_stop_within_walking_straight(stop_id=stop_id_2, walking_time_s=walking_time)
        stops[stop_id_2].add_stop_within_walking_straight(stop_id=stop_id_1, walking_time_s=walking_time)

    for (stop_id_1, stop_id_2), walking_time in walking_times_manhattan.items():
        if walking_time > WALKING_SETTINGS['TIME_WITHIN_WALKING']:
            continue
        stops[stop_id_1].add_stop_within_walking_manhattan(stop_id=stop_id_2, walking_time_s=walking_time)
        stops[stop_id_2].add_stop_within_walking_manhattan(stop_id=stop_id_1, walking_time_s=walking_time)

    return stops, trips, walking_times_straight, walking_times_manhattan




cached_data = load_data_from_cache()

if cached_data:
    stops, trips, walking_times_straight, walking_times_manhattan = cached_data
else:
    stops, trips, walking_times_straight, walking_times_manhattan = process_data()
    save_data_to_cache(stops, trips, walking_times_straight, walking_times_manhattan)


















