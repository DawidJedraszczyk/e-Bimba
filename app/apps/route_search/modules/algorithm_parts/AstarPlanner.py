from haversine import haversine, Unit
import heapq
from itertools import combinations
import numba as nb
import numba.types as nbt
import time

try:
    from django.templatetags.static import static
except:
    pass

from bimba.data.common import INF_TIME, Services
from bimba.data.stops import Stops
from bimba.data.trips import Trips
from .data import Data
from .utils import get_lat_lon_sets, get_closest_shape_point, time_to_seconds, manhattan_distance, custom_print, seconds_to_time
from .Plan import Plan
from .PlanTrip import PlanTrip
from ebus.algorithm_settings import WALKING_SETTINGS, HEURISTIC_SETTINGS, PRINTING_SETTINGS, METRICS_SETTINGS


class AStarPlanner():
    def __init__(self, start_time, START, DESTINATION, distance_metric, current_date,
                 waiting_time_constant=time_to_seconds('00:03:00')):
        start_init_time = time.time()
        self.data = Data.instance()
        self.services = self.data.services_around(current_date)
        self.start_time = start_time
        self.START = START
        self.DESTINATION = DESTINATION
        self.distance_metric = distance_metric
        self.waiting_time_constant = waiting_time_constant
        self.start_walking_times, start_walking_times_time = self.__get_start_walking_times()
        self.destination_walking_times, destination_walking_times_time = self.__get_destination_walking_times()
        self.heuristic_times, precomputed_heurisitc_times_time = self.__get_destination_heurisitc_time()
        self.start_within_walking = self.__get_start_within_walking()
        self.plans_queue = []
        self.found_plans = list()
        self.iterations = 0
        end_init_time = time.time()
        init_time = end_init_time - start_init_time
        self.metrics = {
            'iterations': 0, #i
            'unique_stops_visited': 0, #i
            'plans_queue_max_size': 0, #i
            'expansions_total' : 0, #i sum, over all iterations, of all the stops that were connected to the current stop, there may be repetitions
            'walking_expansions_total': 0, #i
            'trasnit_expansions_total': 0, #i
            'get_next_trips_time_total': 0, #i
            'plan_compute_heurstic_time_total': 0, #i
            'plan_compute_actual_time_total': 0, #i
            'find_plans_time_total': 0, #i
            'planner_initialization_time': init_time, #i
            'start_walking_times_time': start_walking_times_time,
            'destination_walking_times_time' : destination_walking_times_time,
            'precomputed_heurisitc_times_time': precomputed_heurisitc_times_time,
        }
        for stop_id in self.start_within_walking.keys():
            plan = Plan(
                self.start_walking_times,
                self.destination_walking_times,
                self.heuristic_times,
                self.start_time,
                starting_stop_id=stop_id)
            start_time_heuristic = time.time()
            plan.compute_heuristic_time_at_destination()
            end_time_heuristic = time.time()
            self.metrics['plan_compute_heurstic_time_total'] += (end_time_heuristic - start_time_heuristic)
            heapq.heappush(self.plans_queue, plan)
        self.found_plans = list()
        self.iterations = 0

    # TODO: This methods that will be used every time new route is searched,
    # and thus should be optimized for time perfomance
    # Also they must be made more accurate in the future, possibly with help of OSRM

    def __get_start_walking_times(self):
        t0 = time.time()
        if self.distance_metric == 'straight':
            start_walking_times = {
                stop_id: haversine(
                    (stop.coords.lat, stop.coords.lon), self.START,
                    unit=Unit.METERS
                ) / WALKING_SETTINGS['PACE']
                for stop_id, stop in self.data.stops.enumerate()
            }
        elif self.distance_metric == 'manhattan':
            start_walking_times = {
                stop_id: manhattan_distance(
                    stop.coords.lat, stop.coords.lon,
                    self.START[0], self.START[1]
                ) / WALKING_SETTINGS['PACE']
                for stop_id, stop in self.data.stops.enumerate()
            }
        else:
            raise ValueError(f'Unknown distance metric: {self.distance_metric}')
        custom_print(f'(start_walking_times_straight - {time.time() - t0:.4f}s)', 'ALGORITHM_PREPROCESSING_TIMES')
        return start_walking_times, time.time() - t0

    def __get_start_within_walking(self):
        t0 = time.time()
        # TODO - may need to specify incremental increase in case no route found?
        #   or similar "at least X"? or somehow "without explicit"?
        start_within_walking = {
            stop_id: walking_time
            for stop_id, walking_time in self.start_walking_times.items()
            if walking_time <= WALKING_SETTINGS['TIME_WITHIN_WALKING']
        }

        if len(start_within_walking) < 5:
            all_stops = [
                (walking_time, stop_id)
                for stop_id, walking_time in self.start_walking_times.items()
            ]

            all_stops.sort()

            for walking_time, stop_id in all_stops[:5]:
                start_within_walking[stop_id] = walking_time

        custom_print(f'(start_within_walking - {time.time() - t0:.4f}s)', 'ALGORITHM_PREPROCESSING_TIMES')
        return start_within_walking

    def __get_destination_walking_times(self):
        t0 = time.time()
        if self.distance_metric == 'straight':
            destination_walking_times = {
                stop_id: haversine(
                    (stop.coords.lat, stop.coords.lon), self.DESTINATION,
                    unit=Unit.METERS
                ) / WALKING_SETTINGS['PACE']
                for stop_id, stop in self.data.stops.enumerate()
            }
        elif self.distance_metric == 'manhattan':
            destination_walking_times = {
                stop_id: manhattan_distance(
                    stop.coords.lat, stop.coords.lon,
                    self.DESTINATION[0], self.DESTINATION[1]
                ) / WALKING_SETTINGS['PACE']
                for stop_id, stop in self.data.stops.enumerate()
            }
        else:
            raise ValueError(f'Unknown distance metric: {self.distance_metric}')
        custom_print(f'(destination_walking_times_straight - {time.time() - t0:.4f}s)', 'ALGORITHM_PREPROCESSING_TIMES')
        return destination_walking_times, time.time() - t0

    def __get_destination_heurisitc_time(self):
        # This may be overestimating (especially in Manhattan) -> potential problems
        #   BUT note that this may work in practice anyways
        # heuristic = time with tram avg speed to dest + assumed walking time constant
        t0 = time.time()
        if self.distance_metric == 'straight':
            heuristic_times = {
                stop_id: haversine(
                    (stop.coords.lat, stop.coords.lon), self.DESTINATION,
                    unit=Unit.METERS
                ) / HEURISTIC_SETTINGS['MAX_SPEED']
                for stop_id, stop in self.data.stops.enumerate()
            }
        elif self.distance_metric == 'manhattan':
            heuristic_times = {
                stop_id: manhattan_distance(
                    stop.coords.lat, stop.coords.lon,
                    self.DESTINATION[0], self.DESTINATION[1]
                ) / HEURISTIC_SETTINGS['MAX_SPEED']
                for stop_id, stop in self.data.stops.enumerate()
            }
        else:
            raise ValueError(f'Unknown distance metric: {self.distance_metric}')
        custom_print(f'(destination_heuristic_times - {time.time() - t0:.4f}s)', 'ALGORITHM_PREPROCESSING_TIMES')
        return heuristic_times, time.time() - t0

    # Mere algorithm
    def find_next_plan(self):
        start_time_find_next_plan = time.time()
        visited_stops = set()
        while len(self.plans_queue) != 0:
            self.iterations += 1

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
                    custom_print(self.iterations, 'ALGORITHM_ITERATIONS')
                    self.metrics['iterations'] = self.iterations
                    self.metrics['unique_stops_visited'] = len(visited_stops)
                    end_time_find_next_plan = time.time()
                    time_find_next_plan = end_time_find_next_plan - start_time_find_next_plan
                    self.metrics['find_plans_time_total'] += time_find_next_plan
                    return fastest_known_plan
                if len(fastest_known_plan.plan_trips) == 0:
                    plan_accepted = True
                    continue
                last_stop_id = fastest_known_plan.plan_trips[-1].leave_at_stop_id
                # TODO: WARNING - this should to be tested, Most certainly it is wrong for neural network heuristic
                # there may be more effecitive way to the node.
                # The plan should be rejected, only if if it gets to visited stop in longer time
                if last_stop_id not in visited_stops:
                    plan_accepted = True
                    visited_stops.add(last_stop_id)

            # make this plan potential subject for terminal
            # (it was the best option so far and if remains so after we consider its
            # actual walking distance directly => there is no better plan)
            start_time_destinaiton_walking = time.time()
            fastest_known_plan.set_as_terminal()
            end_time_destinaiton_walking = time.time()
            self.metrics['plan_compute_actual_time_total'] += (end_time_destinaiton_walking - start_time_destinaiton_walking)
            # push it back to the queue
            heapq.heappush(self.plans_queue, fastest_known_plan)

            # print(f'visited {fastest_known_plan.current_stop_id}, on {seconds_to_time(fastest_known_plan.current_time)} - time at destination: {seconds_to_time(fastest_known_plan.heuristic_time_at_destination)}, [{fastest_known_plan.arrival_date}]')

            # try extending queue with fastest ways to all reachable stops
            # from stop we're currently at after following fastest known plan yet
            start_time_get_trips = time.time()

            transfer_time = self.waiting_time_constant

            if not fastest_known_plan.plan_trips:
                # Don't add transfer time before first trip
                transfer_time = 0

            fastest_ways = get_next_trips(
                stops = self.data.stops,
                trips = self.data.trips,
                from_stop = fastest_known_plan.current_stop_id,
                services = self.services,
                time = fastest_known_plan.current_time,
                used_trips = fastest_known_plan.used_trips,
                visited_stops = fastest_known_plan.used_stops,
                transfer_time = transfer_time,
                pace = WALKING_SETTINGS["PACE"],
            )

            end_time_get_trips = time.time()
            self.metrics['get_next_trips_time_total'] += (end_time_get_trips - start_time_get_trips)

            walking_trips_found = 0

            ## create extended plans and add them to the queue
            for stop_id, extending_plan_trip in fastest_ways.items():
                if extending_plan_trip.trip_id == -1:
                    walking_trips_found += 1

                extended_plan = Plan(self.start_walking_times,
                                     self.destination_walking_times,
                                     self.heuristic_times,
                                     fastest_known_plan.start_time,
                                     plan_trips=fastest_known_plan.plan_trips + [extending_plan_trip],
                                     prev_inconvenience=fastest_known_plan.inconvenience)
                start_time_heuristic = time.time()
                extended_plan.compute_heuristic_time_at_destination()
                end_time_heuristic = time.time()
                self.metrics['plan_compute_heurstic_time_total'] += (end_time_heuristic - start_time_heuristic)
                heapq.heappush(self.plans_queue, extended_plan)

            if METRICS_SETTINGS['EXPANSIONS']:
                self.metrics['trasnit_expansions_total'] += len(fastest_ways) - walking_trips_found
                self.metrics['walking_expansions_total'] += walking_trips_found
                self.metrics['expansions_total'] += len(fastest_ways)
                if len(self.plans_queue) > self.metrics['plans_queue_max_size']:
                    self.metrics['plans_queue_max_size'] = len(self.plans_queue)

    def plans_to_html(self):
        response = {}

        for index, plan in enumerate(self.found_plans):
            communication = []
            start_time = None
            destination_time = seconds_to_time(plan.time_at_destination)

            for plan_trip in plan.plan_trips:
                if plan_trip.trip_id != -1:
                    if not start_time:
                        start_time = seconds_to_time(plan_trip.departure_time)

                    route_id = self.data.trips[plan_trip.trip_id].route_id
                    communication.append(self.data.routes[route_id].name)

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

    def prepare_coords(self, plan_num: int):
        response = {}

        plan = self.found_plans[plan_num]

        for index, plan_trip in enumerate(plan.plan_trips):
            start_stop = self.data.stops[plan_trip.start_from_stop_id]
            goal_stop = self.data.stops[plan_trip.leave_at_stop_id]

            if index == 0:
                response[0] = [self.START, (start_stop.coords.lat, start_stop.coords.lon)]

            if index == len(plan.plan_trips) - 1:
                response[len(plan.plan_trips) + 1] = [(goal_stop.coords.lat, goal_stop.coords.lon), self.DESTINATION]

            if plan_trip.trip_id != -1:
                trip = self.data.trips[plan_trip.trip_id]
                shape_id = trip.shape_id
                points = self.data.shapes.get_points_between(shape_id, start_stop.coords, goal_stop.coords)
                response[index + 1] = [(p.lat, p.lon) for p in points]
            else:
                response[index + 1] = [
                    (start_stop.coords.lat, start_stop.coords.lon),
                    (goal_stop.coords.lat, goal_stop.coords.lon),
                ]

        return response

    def prepare_departure_details(self, plan_num: int, start_location: str, goal_location: str):
        response = {}

        plan = self.found_plans[plan_num]

        for index, plan_trip in enumerate(plan.plan_trips):
            start_stop = self.data.stops[plan_trip.start_from_stop_id]
            goal_stop = self.data.stops[plan_trip.leave_at_stop_id]

            if index == 0:
                response[0] = f'''
                    <div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;">
                        <img style="width: 25px;" src="{static('base_view/img/WALK.png')}">
                        <span style="margin-left: 10px; text-align: left;">
                            {start_location} -> {start_stop.name}
                        </span>
                    </div>
                '''

            if index == len(plan.plan_trips) - 1:
                response[len(plan.plan_trips) + 1] = f'''
                    <div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;">
                        <img style="width: 25px;" src="{static('base_view/img/WALK.png')}">
                        <span style="margin-left: 10px; text-align: left;">
                            {goal_stop.name} -> {goal_location}
                        </span>
                    </div>
                '''

            departure_time = seconds_to_time(plan_trip.departure_time)
            arrival_time = seconds_to_time(plan_trip.arrival_time)

            if plan_trip.trip_id != -1:
                trip = self.data.trips[plan_trip.trip_id]
                route = self.data.routes[trip.route_id].name
                direction = trip.headsign
                response[
                    index + 1] = f'''<div style="display: flex; width: 90%; flex-direction: column; justify-content: center; margin: 10px 0;"><div style="display:flex; align-items: center; margin: 10px 0;"><img src="{static('base_view/img/BUS.svg')}" alt="bus icon"/><span style="margin-left: 10px;">{route} - {direction} ({departure_time} - {arrival_time})</span></div><div class="stops" style="font-size: 14px; text-align: left;">'''

                in_our_trip_flag = False
                time_offset = 0

                for stop_id, arrival, departure in self.data.trips.get_trip_stops(plan_trip.trip_id):
                    if stop_id == plan_trip.start_from_stop_id:
                        in_our_trip_flag = True
                        time_offset = departure
                        relevant_time = departure
                    else:
                        relevant_time = arrival

                    if in_our_trip_flag:
                        time = relevant_time - time_offset + plan_trip.departure_time
                        stop = self.data.stops[stop_id]
                        response[index + 1] += f'''{seconds_to_time(time)} {stop.name}<br>'''

                    if stop_id == plan_trip.leave_at_stop_id:
                        in_our_trip_flag = False

            else:
                response[index + 1] = f'''
                    <div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;">
                        <img style="width: 25px;" src="{static('base_view/img/WALK.png')}">
                        <span style="margin-left: 10px; text-align: left;">
                            {start_stop.name} -> {goal_stop.name}  ({departure_time} - {arrival_time})
                        </span>
                    </div>
                '''

            response[index + 1] += "</div></div>"

        return response


_NB_PLAN_TRIP_TYPE = nbt.NamedUniTuple(nb.int32, 5, PlanTrip)
_COMPILATION_T0 = time.time()

@nb.jit(
    nbt.DictType(nb.int32, _NB_PLAN_TRIP_TYPE)
    (
        Stops.class_type.instance_type,
        Trips.class_type.instance_type,
        nb.int64,
        Services.class_type.instance_type,
        nb.int64,
        nbt.Set(nb.int64, True),
        nbt.Set(nb.int64, True),
        nb.int64,
        nb.float64,
    ),
)
def get_next_trips(
    stops: Stops,
    trips: Trips,
    from_stop: int,
    services: Services,
    time: int,
    used_trips: set,
    visited_stops: set,
    transfer_time: int,
    pace: float,
) -> dict[int, PlanTrip]:
    fastest_ways = nb.typed.Dict.empty(nb.int32, _NB_PLAN_TRIP_TYPE)
    from_stop = nb.int32(from_stop)
    time = nb.int32(time)

    for to_stop, distance in stops.get_stop_walks(from_stop):
        if to_stop in visited_stops:
            continue

        time_at_stop = time + nb.int32(distance / pace)

        fastest_ways[to_stop] = PlanTrip(
            trip_id = nb.int32(-1),
            start_from_stop_id = from_stop,
            departure_time = time,
            leave_at_stop_id = to_stop,
            arrival_time = nb.int32(time_at_stop),
        )

    for trip_id, from_seq, stop_departure in stops.get_stop_trips(from_stop):
        if trip_id in used_trips:
            continue

        min_start = time + transfer_time - stop_departure
        start_time = trips.get_next_start(trip_id, services, min_start)

        if start_time == INF_TIME:
            continue

        for to_stop, stop_arrival, _ in trips.get_stops_after(trip_id, from_seq):
            if to_stop in visited_stops:
                continue

            arrival = start_time + stop_arrival

            if to_stop not in fastest_ways or fastest_ways[to_stop].arrival_time > arrival:
                fastest_ways[to_stop] = PlanTrip(
                    trip_id = trip_id,
                    start_from_stop_id = from_stop,
                    departure_time = nb.int32(start_time + stop_departure),
                    leave_at_stop_id = to_stop,
                    arrival_time = nb.int32(arrival),
                )

    return fastest_ways


custom_print(f'(jit get_next_trips - {time.time() - _COMPILATION_T0:.4f}s)', 'SETUP_TIMES')
