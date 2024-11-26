from dataclasses import dataclass
import heapq
from itertools import combinations
import numba as nb
import numba.types as nbt
import time

try:
    from django.templatetags.static import static
except:
    pass

from bimba.data.misc import Coords, INF_TIME, Services
from bimba.data.stops import Stops
from bimba.data.trips import Trips
from bimba.prospector import Prospect
from .data import Data
from .estimator import Estimates, Estimator, EuclideanEstimator
from .utils import get_lat_lon_sets, get_closest_shape_point, time_to_seconds, manhattan_distance, custom_print, seconds_to_time
from .Plan import Plan
from .PlanTrip import PlanTrip
from ebus.algorithm_settings import WALKING_SETTINGS, HEURISTIC_SETTINGS, PRINTING_SETTINGS, METRICS_SETTINGS


class AStarPlanner():
    def __init__(
        self,
        data: Data,
        start: Coords,
        destination: Coords,
        date,
        start_time,
        estimator_factory=EuclideanEstimator,
    ):
        start_init_time = time.time()
        self.prospect = data.prospector.prospect(start, destination)
        prospecting_time = time.time() - start_init_time

        self.data = data
        self.services = self.data.services_around(date)
        self.start_time = start_time

        self.estimator = estimator_factory(
            data.stops,
            self.prospect.destination,
            self.prospect.near_destination,
        )

        self.iterations = 0
        self.plans_queue = []
        self.found_plans = list()
        self.visited_stops = {}
        self.discovered_stops = {}

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
            'planner_initialization_time': 0, #i
            'plans_queue_operations_time': 0,
            'plan_accepting_time': 0,
            'extended_plans_initialization_time': 0,
            'prospecting_time': prospecting_time,
        }

        for near in self.prospect.near_start:
            walk_time = int(near.walk_distance / WALKING_SETTINGS["PACE"])
            estimates = self.estimate(near.id, start_time + walk_time)
            plan = Plan.from_start(start_time, near.id, walk_time, estimates)
            self.discovered_stops[near.id] = plan
            self.plans_queue.append(plan)

        heapify_t0 = time.time()
        heapq.heapify(self.plans_queue)
        self.metrics['plans_queue_operations_time'] += (time.time() - heapify_t0)

        end_init_time = time.time()
        init_time = end_init_time - start_init_time
        self.metrics['find_plans_time_total'] += init_time

        self.metrics['planner_initialization_time'] = (
            init_time
            - prospecting_time
            - self.metrics['plan_compute_heurstic_time_total']
            - self.metrics['plans_queue_operations_time']
        )

    def estimate(self, stop_id: int, at_time: int) -> Estimates:
        t0 = time.time()
        estimates = self.estimator.estimate(stop_id, at_time)
        self.metrics['plan_compute_heurstic_time_total'] += time.time() - t0
        return estimates

    # Mere algorithm
    def find_next_plan(self):
        start_time_find_next_plan = time.time()
        while len(self.plans_queue) != 0:
            self.iterations += 1

            if not self.plans_queue:
                raise Exception('no more plans')

            start_plan_accepting_time = time.time()
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
                    self.metrics['unique_stops_visited'] = len(self.visited_stops)
                    end_time_find_next_plan = time.time()
                    time_find_next_plan = end_time_find_next_plan - start_time_find_next_plan
                    self.metrics['find_plans_time_total'] += time_find_next_plan
                    return fastest_known_plan
                if len(fastest_known_plan.plan_trips) == 0:
                    plan_accepted = True
                    continue
                last_stop_id = fastest_known_plan.plan_trips[-1].to_stop
                # TODO: WARNING - this should to be tested, Most certainly it is wrong for neural network heuristic
                # there may be more effecitive way to the node.
                # The plan should be rejected, only if if it gets to visited stop in longer time
                if last_stop_id not in self.visited_stops.keys() or self.visited_stops[last_stop_id] > fastest_known_plan.current_time:
                    plan_accepted = True
                    self.visited_stops[last_stop_id] = fastest_known_plan.current_time
            end_plan_accepting_time = time.time()
            self.metrics['plan_accepting_time'] += (end_plan_accepting_time - start_plan_accepting_time)

            # make this plan potential subject for terminal
            # (it was the best option so far and if remains so after we consider its
            # actual walking distance directly => there is no better plan)
            start_time_destinaiton_walking = time.time()
            fastest_known_plan.set_as_terminal()
            end_time_destinaiton_walking = time.time()
            self.metrics['plan_compute_actual_time_total'] += (end_time_destinaiton_walking - start_time_destinaiton_walking)
            # push it back to the queue
            start_time_heappush = time.time()
            heapq.heappush(self.plans_queue, fastest_known_plan)
            end_time_heappush = time.time()
            self.metrics['plans_queue_operations_time'] += (end_time_heappush-start_time_heappush)

            # print(f'visited {fastest_known_plan.current_stop_id}, on {seconds_to_time(fastest_known_plan.current_time)} - time at destination: {seconds_to_time(fastest_known_plan.heuristic_time_at_destination)}, [{fastest_known_plan.arrival_date}]')

            # try extending queue with fastest ways to all reachable stops
            # from stop we're currently at after following fastest known plan yet
            start_time_get_trips = time.time()

            transfer_time = HEURISTIC_SETTINGS["TRANSFER_TIME"]

            if not fastest_known_plan.plan_trips:
                # Don't add transfer time before first trip
                transfer_time = 0

            fastest_ways = get_next_trips(
                stops = self.data.stops,
                trips = self.data.trips,
                from_stop = fastest_known_plan.current_stop_id,
                services = self.services,
                time = fastest_known_plan.current_time,
                transfer_time = transfer_time,
                pace = WALKING_SETTINGS["PACE"],
            )

            end_time_get_trips = time.time()
            self.metrics['get_next_trips_time_total'] += (end_time_get_trips - start_time_get_trips)

            walking_trips_found = 0

            start_extensions_init_time = time.time()
            extended_plans = []
            compute_heurstic_time = 0
            ## create extended plans and add them to the queue
            for stop_id, extending_plan_trip in fastest_ways.items():
                if extending_plan_trip.trip_id == -1:
                    walking_trips_found += 1

                cur_time = extending_plan_trip.arrival_time
                prev_plan = self.discovered_stops.get(stop_id, None)

                if prev_plan is not None and prev_plan.current_time < cur_time:
                    continue

                if (
                    prev_plan is not None and
                    prev_plan.estimates.at_time - cur_time <= self.estimator.TIME_VALID
                ):
                    estimates = prev_plan.estimates
                else:
                    estimates = self.estimate(stop_id, cur_time)

                plan = fastest_known_plan.extend(extending_plan_trip, estimates)

                if prev_plan is None or plan < prev_plan:
                    self.discovered_stops[stop_id] = plan
                    extended_plans.append(plan)

            end_extensions_init_time = time.time()

            start_time_heappush = time.time()
            for plan in extended_plans:
                heapq.heappush(self.plans_queue, plan)
            end_time_heappush = time.time()

            self.metrics['plan_compute_heurstic_time_total'] += compute_heurstic_time
            self.metrics['extended_plans_initialization_time'] += (end_extensions_init_time-start_extensions_init_time) - compute_heurstic_time
            self.metrics['plans_queue_operations_time'] += (end_time_heappush-start_time_heappush)
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
                'div': f'''<div style="display:none"></div><div id="{index}" class="solution" style="cursor: pointer; width: 99%; border: solid 1px white; padding: 20px 0px; border-radius: 5px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;"> <div style="font-size: 25px; margin-left: 5px;">{start_time}</div><div style="display: flex;">{communication_content}</div><div style="font-size: 25px; margin-right: 5px;">{destination_time}</div></div>'''
            }
            response[str(index)] = prepared_solution
        return response

    def prepare_coords(self, plan_num: int):
        response = {}

        plan = self.found_plans[plan_num]

        for index, plan_trip in enumerate(plan.plan_trips):
            start_stop = self.data.stops[plan_trip.from_stop]
            goal_stop = self.data.stops[plan_trip.to_stop]

            if index == 0:
                response[0] = [
                    (self.prospect.start_coords.lat, self.prospect.start_coords.lon),
                    (start_stop.coords.lat, start_stop.coords.lon),
                ]

            if index == len(plan.plan_trips) - 1:
                response[len(plan.plan_trips) + 1] = [
                    (goal_stop.coords.lat, goal_stop.coords.lon),
                    (self.prospect.destination_coords.lat, self.prospect.destination_coords.lon),
                ]

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
            start_stop = self.data.stops[plan_trip.from_stop]
            goal_stop = self.data.stops[plan_trip.to_stop]

            if index == 0:
                response[0] = f'''<div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;"><img style="width: 25px;" src="{static('base_view/img/WALK.png')}"><span style="margin-left: 10px; text-align: left;">{start_location} -> {start_stop.name}</span></div>'''

            if index == len(plan.plan_trips) - 1:
                response[len(plan.plan_trips) + 1] = f'''<div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;"><img style="width: 25px;" src="{static('base_view/img/WALK.png')}"><span style="margin-left: 10px; text-align: left;">{goal_stop.name} -> {goal_location}</span></div>'''

            departure_time = seconds_to_time(plan_trip.departure_time)
            arrival_time = seconds_to_time(plan_trip.arrival_time)

            if plan_trip.trip_id != -1:
                trip = self.data.trips[plan_trip.trip_id]
                route = self.data.routes[trip.route_id].name
                direction = trip.headsign


                response[index + 1] = f'''<div class="departure-details" style="display: flex; width: 90%; flex-direction: column; justify-content: center; margin: 10px 0;"><div style="display:flex; align-items: center; margin: 10px 0;"><img src="{static('base_view/img/BUS.svg')}" alt="bus icon"/><span style="margin-left: 10px;">{route} - {direction} ({departure_time} - {arrival_time})</span></div><div class="stops" style="font-size: 14px; text-align: left;">'''

                in_our_trip_flag = False
                time_offset = 0

                for stop_sequence, (stop_id, arrival, departure) in enumerate(self.data.trips.get_trip_stops(plan_trip.trip_id)):
                    if stop_id == plan_trip.from_stop:
                        in_our_trip_flag = True
                        time_offset = departure
                        relevant_time = departure
                    else:
                        relevant_time = arrival

                    if in_our_trip_flag:
                        time = relevant_time - time_offset + plan_trip.departure_time
                        stop = self.data.stops[stop_id]
                        response[index + 1] += f'''<div class="departure-time" data-sequence-number={stop_sequence}>{seconds_to_time(time)} {stop.name}</div>'''

                    if stop_id == plan_trip.to_stop:
                        in_our_trip_flag = False

            else:
                response[index + 1] = f'''<div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;"><img style="width: 25px;" src="{static('base_view/img/WALK.png')}"><span style="margin-left: 10px; text-align: left;">{start_stop.name} -> {goal_stop.name}  ({departure_time} - {arrival_time})</span></div>'''

            response[index + 1] += "</div></div>"

        return response


    def prepare_gtfs_trip_ids(self, plan_num: int):
        response = {}

        plan = self.found_plans[plan_num]

        for index, plan_trip in enumerate(plan.plan_trips):
            if plan_trip.trip_id != -1:
                response[index] = self.data.tdb.get_trip_instance(
                    plan_trip.trip_id,
                    plan_trip.service_id,
                    plan_trip.trip_start
                ).gtfs_trip_id

        return response

_NB_PLAN_TRIP_TYPE = nbt.NamedUniTuple(nb.int32, 7, PlanTrip)
_COMPILATION_T0 = time.time()

@nb.jit(
    nbt.DictType(nb.int32, _NB_PLAN_TRIP_TYPE)
    (
        Stops.class_type.instance_type,
        Trips.class_type.instance_type,
        nb.int64,
        Services.class_type.instance_type,
        nb.int64,
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
    transfer_time: int,
    pace: float,
) -> dict[int, PlanTrip]:
    fastest_ways = nb.typed.Dict.empty(nb.int32, _NB_PLAN_TRIP_TYPE)
    from_stop = nb.int32(from_stop)
    time = nb.int32(time)

    for to_stop, distance in stops.get_stop_walks(from_stop):
        time_at_stop = time + nb.int32(distance / pace)

        fastest_ways[to_stop] = PlanTrip(
            trip_id = nb.int32(-1),
            service_id = nb.int32(-1),
            trip_start = nb.int32(-1),
            from_stop = from_stop,
            departure_time = time,
            to_stop = to_stop,
            arrival_time = nb.int32(time_at_stop),
        )

    for trip_id, from_seq, stop_departure in stops.get_stop_trips(from_stop):
        min_start = time + transfer_time - stop_departure
        start = trips.get_next_start(trip_id, services, min_start)

        if start.time == INF_TIME:
            continue

        for to_stop, stop_arrival, _ in trips.get_stops_after(trip_id, from_seq):
            arrival = start.time + stop_arrival

            if to_stop not in fastest_ways or fastest_ways[to_stop].arrival_time > arrival:
                fastest_ways[to_stop] = PlanTrip(
                    trip_id = trip_id,
                    service_id = start.service,
                    trip_start = nb.int32(start.time - start.offset),
                    from_stop = from_stop,
                    departure_time = nb.int32(start.time + stop_departure),
                    to_stop = to_stop,
                    arrival_time = nb.int32(arrival),
                )

    return fastest_ways


custom_print(f'(jit get_next_trips - {time.time() - _COMPILATION_T0:.4f}s)', 'SETUP_TIMES')
