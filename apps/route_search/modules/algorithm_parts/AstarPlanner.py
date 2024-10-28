import heapq
from time import time
from haversine import haversine, Unit
from itertools import combinations

from algorithm_parts.utils import get_next_day, time_to_seconds, get_previous_day, manhattan_distance, custom_print
from algorithm_parts.Plan import Plan
from algorithm_parts.PlanTrip import PlanTrip
from algorithm_parts.DataLoaderSingleton import initialized_dataloader_singleton
from ebus.algorithm_settings import WALKING_SETTINGS, HEURISTIC_SETTINGS, PRINTING_SETTINGS


class AStarPlanner():
    def __init__(self, start_time, START, DESTINATION, distance_metric, current_date,
                 waiting_time_constant=time_to_seconds('00:03:00')):
        data_loader = initialized_dataloader_singleton
        self.stops = data_loader.get_stops()
        self.trips = data_loader.get_trips()
        self.start_time = start_time
        self.START = START
        self.DESTINATION = DESTINATION
        self.distance_metric = distance_metric
        self.waiting_time_constant = waiting_time_constant
        self.start_walking_times = self.__get_start_walking_times()
        self.destination_walking_times = self.__get_destination_walking_times()
        self.heuristic_times = self.__get_destination_heurisitc_time()
        self.start_within_walking = self.__get_start_within_walking()
        self.plans_queue = []
        for stop_id in self.start_within_walking.keys():
            plan = Plan(
                self.start_walking_times,
                self.destination_walking_times,
                self.heuristic_times,
                self.start_time,
                current_date,
                starting_stop_id=stop_id)
            heapq.heappush(self.plans_queue, plan)
        self.found_plans = list()
        self.iterations = 0

    # returns negative value if fastest_way is faster than alternative_way
    def __compute_trips_arrival_time_difference(self, fastest_way, alternative_way_arrival_time_s,
                                                alterntaive_way_date):
        if fastest_way.date == alterntaive_way_date:
            difference = fastest_way.arrival_time - alternative_way_arrival_time_s
        elif fastest_way.date == get_previous_day(alterntaive_way_date):
            difference = fastest_way.arrival_time - (alternative_way_arrival_time_s + time_to_seconds('24:00:00'))
        elif fastest_way.date == get_next_day(alterntaive_way_date):
            difference = fastest_way.arrival_time - (alternative_way_arrival_time_s - time_to_seconds('24:00:00'))
        else:
            raise ValueError(f"Dates of arrival are too far apart: {fastest_way.date} and {alterntaive_way_date}")
        return difference

    # TODO: This methods that will be used every time new route is searched,
    # and thus should be optimized for time perfomance
    # Also they must be made more accurate in the future, possibly with help of OSRM

    def __get_start_walking_times(self):
        t0 = time()
        if self.distance_metric == 'straight':
            start_walking_times = {
                stop.stop_id: haversine(
                    (stop.stop_lat, stop.stop_lon), self.START,
                    unit=Unit.METERS
                ) / WALKING_SETTINGS['PACE']
                for stop in self.stops.values()
            }
        elif self.distance_metric == 'manhattan':
            start_walking_times = {
                stop.stop_id: manhattan_distance(
                    stop.stop_lat, stop.stop_lon,
                    self.START[0], self.START[1]
                ) / WALKING_SETTINGS['PACE']
                for stop in self.stops.values()
            }
        else:
            raise ValueError(f'Unknown distance metric: {self.distance_metric}')
        custom_print(f'(start_walking_times_straight - {time() - t0:.4f}s)', 'ALGORITHM_PREPROCESSING_TIMES')
        return start_walking_times

    def __get_start_within_walking(self):
        t0 = time()
        # TODO - may need to specify incremental increase in case no route found?
        #   or similar "at least X"? or somehow "without explicit"?
        start_within_walking = {
            stop_id: walking_time
            for stop_id, walking_time in self.start_walking_times.items()
            if walking_time <= WALKING_SETTINGS['TIME_WITHIN_WALKING']
        }
        custom_print(f'(start_within_walking - {time() - t0:.4f}s)', 'ALGORITHM_PREPROCESSING_TIMES')
        return start_within_walking

    def __get_destination_walking_times(self):
        t0 = time()
        if self.distance_metric == 'straight':
            destination_walking_times = {
                stop.stop_id: haversine(
                    (stop.stop_lat, stop.stop_lon), self.DESTINATION,
                    unit=Unit.METERS
                ) / WALKING_SETTINGS['PACE']
                for stop in self.stops.values()
            }
        elif self.distance_metric == 'manhattan':
            destination_walking_times = {
                stop.stop_id: manhattan_distance(
                    stop.stop_lat, stop.stop_lon,
                    self.DESTINATION[0], self.DESTINATION[1]
                ) / WALKING_SETTINGS['PACE']
                for stop in self.stops.values()
            }
        else:
            raise ValueError(f'Unknown distance metric: {self.distance_metric}')
        custom_print(f'(destination_walking_times_straight - {time() - t0:.4f}s)', 'ALGORITHM_PREPROCESSING_TIMES')
        return destination_walking_times

    def __get_destination_heurisitc_time(self):
        # This may be overestimating (especially in Manhattan) -> potential problems
        #   BUT note that this may work in practice anyways
        # heuristic = time with tram avg speed to dest + assumed walking time constant
        t0 = time()
        if self.distance_metric == 'straight':
            heuristic_times = {
                stop.stop_id: haversine(
                    (stop.stop_lat, stop.stop_lon), self.DESTINATION,
                    unit=Unit.METERS
                ) / WALKING_SETTINGS['PACE'] + HEURISTIC_SETTINGS['ALWAYS_WALKING_TIME_CONSTANT']
                for stop in self.stops.values()
            }
        elif self.distance_metric == 'manhattan':
            heuristic_times = {
                stop.stop_id: manhattan_distance(
                    stop.stop_lat, stop.stop_lon,
                    self.DESTINATION[0], self.DESTINATION[1]
                ) / HEURISTIC_SETTINGS['MAX_SPEED'] + HEURISTIC_SETTINGS['ALWAYS_WALKING_TIME_CONSTANT']
                for stop in self.stops.values()
            }
        else:
            raise ValueError(f'Unknown distance metric: {self.distance_metric}')
        custom_print(f'(destination_heuristic_times - {time() - t0:.4f}s)', 'ALGORITHM_PREPROCESSING_TIMES')
        return heuristic_times

    # Mere algorithm
    def find_next_plan(self):
        visited_stops = set()
        while len(self.plans_queue) != 0:
            self.iterations += 1
            # print('iteration', self.iterations)

            if not self.plans_queue:
                raise Exception('no more plans')

            # remove fastest known plan yet from queue
            t = time()
            plan_accepted = False
            while not plan_accepted:
                fastest_known_plan = heapq.heappop(self.plans_queue)
                # if this it True, it means that:
                # - heuristic doesn't point at anything potentially better
                # - among terminal plans in the queue, this is the fastest
                if fastest_known_plan.is_terminal:
                    self.found_plans.append(fastest_known_plan)
                    custom_print(self.iterations, 'ALGORITHM_ITERATIONS')
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

            # print(f'visited {fastest_known_plan.current_stop_id}, on {seconds_to_time(fastest_known_plan.current_time)} - time at destination: {seconds_to_time(fastest_known_plan.heuristic_time_at_destination)}, [{fastest_known_plan.arrival_date}]')

            # try extending queue with **fastest** ways to **all** reachable stops
            # from stop we're currently at after following fastest known plan yet
            current_stop = self.stops[fastest_known_plan.current_stop_id]
            fastest_ways = dict()
            ## factor in trips from this stop directly
            available_trips = current_stop.get_next_trips(
                start_time_s=fastest_known_plan.current_time + self.waiting_time_constant,
                date_str=fastest_known_plan.arrival_date)
            if available_trips:
                for trip_id, (stop_index_in_sequence, departure_time, trip_date) in available_trips.items():
                    if trip_id in fastest_known_plan.used_trips:
                        continue  # covered in other plans, would be duplication
                    trip = self.trips[trip_id]
                    for i in range(stop_index_in_sequence + 1, len(trip.stop_ids)):
                        stop_id, arrival_time = trip.stop_ids[i], trip.arrival_times_s[i]
                        if stop_id not in fastest_ways.keys() or self.__compute_trips_arrival_time_difference(
                                fastest_ways[stop_id],
                                arrival_time,
                                trip_date) > 0:
                            fastest_ways[stop_id] = PlanTrip(
                                trip_id=trip_id,
                                start_from_stop_id=current_stop.stop_id,
                                departure_time=departure_time,
                                leave_at_stop_id=stop_id,
                                arrival_time=arrival_time,
                                type='bus',  # TODO - change when distinction between buses and trams is implemented
                                date=trip_date
                            )
            # else:
            # print('NO TRIPS AVAILABLE!')
            ## factor in stops within walking distance
            bus_trips_found = len(fastest_ways)
            # print('new_bus_trips_found = ',bus_trips_found)
            # if bus_trips_found == 0:
            # print(available_trips)

            for stop_id, walking_time in current_stop.stops_within_walking_straight.items():
                # TODO - get exact walking time
                # print(stop_id)
                # print(fastest_known_plan.used_stops)
                if stop_id not in fastest_known_plan.used_stops:
                    time_at_stop = fastest_known_plan.current_time + walking_time + HEURISTIC_SETTINGS[
                        'ALWAYS_WALKING_TIME_CONSTANT']
                    # if stop_id not in fastest_ways.keys() or fastest_ways[stop_id][2] > arrival_time:
                    if stop_id not in fastest_ways.keys() or self.__compute_trips_arrival_time_difference(
                            fastest_ways[stop_id],
                            time_at_stop,
                            fastest_known_plan.arrival_date) > 0:
                        fastest_ways[stop_id] = PlanTrip(
                            trip_id=None,
                            start_from_stop_id=current_stop.stop_id,
                            departure_time=fastest_known_plan.current_time,
                            leave_at_stop_id=stop_id,
                            arrival_time=time_at_stop,
                            type='WALK',
                            date=fastest_known_plan.arrival_date
                        )
                    # else:
                    # print('STOP ALREADY DISCOVERED, with faster time!')
                # else:
                # print('STOP ALREADY USED!')
            ## create extended plans and add them to the queue
            stops_within_walking_found = len(fastest_ways) - bus_trips_found
            # print('stops_within_walking_found:', stops_within_walking_found)

            for stop_id, extending_plan_trip in fastest_ways.items():
                extended_plan = Plan(self.start_walking_times,
                                     self.destination_walking_times,
                                     self.heuristic_times,
                                     fastest_known_plan.start_time,
                                     extending_plan_trip.date,
                                     plan_trips=fastest_known_plan.plan_trips + [extending_plan_trip])
                heapq.heappush(self.plans_queue, extended_plan)
