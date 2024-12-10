import datetime
import heapq
from itertools import combinations
import numba as nb
import numba.types as nbt
import time

from .data import Data
from .discovered_stop import DiscoveredStop
from .estimator import Estimate, Estimator, Instant
from .plan import Plan, PlanTrip
from .utils import *
from ebus.algorithm_settings import *
from transit.data.misc import Coords, INF_TIME, Services
from transit.data.stops import Stops
from transit.data.trips import Trips
from transit.prospector import Prospect


class AStarPlanner():
    prospect: Prospect
    data: Data
    services: Services
    date: datetime.date
    start_time: int
    estimator: Estimator
    iterations: int
    plans_queue: list[Plan]
    found_plans: list[Plan]
    used_trips: set[frozenset[tuple[int, int]]]
    shortest_time: int
    visited_stops: set[int]
    discovered_stops: dict[int, DiscoveredStop]
    walk_times: dict[int, int]
    estimates: dict[int, Estimate]

    def __init__(
        self,
        data: Data,
        start: Coords,
        destination: Coords,
        date: datetime.date,
        start_time,
        estimator=None,
    ):
        start_init_time = time.time()
        self.prospect = data.prospector.prospect(start, destination)
        prospecting_time = time.time() - start_init_time

        self.data = data

        if not isinstance(date, datetime.date):
            date = datetime.date.fromisoformat(date)
            custom_print(f'Invalid date format: {date}', 'DEBUG')
        self.date = date
    
        self.services = self.data.services_around(self.date)
        self.start_time = start_time
        self.estimator = estimator or data.default_estimator

        self.iterations = 0
        self.plans_queue = []
        self.found_plans = []
        self.used_trips = set()
        self.shortest_time = INF_TIME
        self.visited_stops = set()
        self.discovered_stops = {}
        self.walk_times = {}
        self.estimates = {}

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

        for near in self.prospect.near_destination:
            self.walk_times[near.id] = int(near.walk_distance / WALKING_SETTINGS["PACE"])

        for near in self.prospect.near_start:
            walk_time = int(near.walk_distance / WALKING_SETTINGS["PACE"])
            dstop = self.discover_stop(near.id)
            plan = Plan.initial(near.id, start_time, walk_time)
            plan.walk_time = self.get_walk_time(near.id)
            plan.travel_time = self.get_estimate(near.id, start_time + walk_time).travel_time
            dstop.register_plan(plan)
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

    def get_walk_time(self, stop_id: int) -> int:
        wt = self.walk_times.get(stop_id)

        if wt is None:
            distance = self.data.stops[stop_id].position.distance(self.prospect.destination)
            wt = int(distance * WALKING_SETTINGS["DISTANCE_MULTIPLIER"] / WALKING_SETTINGS["PACE"])
            self.walk_times[stop_id] = wt

        return wt

    def estimate(self, stop_id: int, at_time: int) -> Estimate:
        t0 = time.time()
        instant = Instant.from_date(self.date, at_time)
        travel_time = self.estimator.estimate(self.data.stops, self.prospect, stop_id, instant)
        self.metrics['plan_compute_heurstic_time_total'] += time.time() - t0
        return Estimate(travel_time, at_time)

    def is_estimate_valid(self, estimates: Estimate, at_time: int) -> bool:
        return abs(estimates.at_time - at_time) <= self.estimator.time_valid

    def discover_stop(self, stop_id: int) -> DiscoveredStop:
        dstop = self.discovered_stops.get(stop_id)

        if dstop is None:
            dstop = DiscoveredStop({})
            self.discovered_stops[stop_id] = dstop
            return dstop

        return dstop

    def get_estimate(self, stop_id: int, at_time: int) -> Estimate:
        estimate = self.estimates.get(stop_id)

        if estimate is None or not self.is_estimate_valid(estimate, at_time):
            estimate = self.estimate(stop_id, at_time)
            self.estimates[stop_id] = estimate

        return estimate

    # Mere algorithm
    def find_next_plan(self):
        start_time_find_next_plan = time.time()
        start_plan_accepting_time = start_time_find_next_plan

        while self.plans_queue:
            # remove fastest known plan yet from queue
            fastest_known_plan = heapq.heappop(self.plans_queue)

            # if this it True, it means that:
            # - heuristic doesn't point at anything potentially better
            # - among terminal plans in the queue, this is the fastest
            if fastest_known_plan.walk_time == 0:
                used_trips = fastest_known_plan.get_used_trip_instances()

                if self.is_accepatble_alternative(fastest_known_plan, used_trips):
                    self.used_trips.add(used_trips)
                else:
                    continue

                t = time.time()
                self.metrics['plan_accepting_time'] += t - start_plan_accepting_time
                self.metrics['find_plans_time_total'] += t - start_time_find_next_plan
                self.metrics['iterations'] = self.iterations
                self.metrics['unique_stops_visited'] = len(self.visited_stops)
                custom_print(self.iterations, 'ALGORITHM_ITERATIONS')

                self.next_gen(fastest_known_plan)
                self.found_plans.append(fastest_known_plan)

                return fastest_known_plan

            # We've already encountered a plan that arrived at this stop with a better (lower) score
            if fastest_known_plan.superseded:
                continue

            self.iterations += 1
            self.visited_stops.add(fastest_known_plan.current_stop_id)

            end_plan_accepting_time = time.time()
            self.metrics['plan_accepting_time'] += (end_plan_accepting_time - start_plan_accepting_time)

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
            extended_plans = [fastest_known_plan.extend_to_destination()]
            compute_heurstic_time_before = self.metrics['plan_compute_heurstic_time_total']

            ## create extended plans and add them to the queue
            for stop_id, extending_plan_trip in fastest_ways.items():
                if extending_plan_trip.trip_id == -1:
                    walking_trips_found += 1

                dstop = self.discover_stop(stop_id)
                plan = fastest_known_plan.extend(extending_plan_trip)

                if dstop.register_plan(plan):
                    cur_time = extending_plan_trip.arrival_time
                    plan.walk_time = self.get_walk_time(stop_id)
                    plan.travel_time = self.get_estimate(stop_id, cur_time).travel_time
                    extended_plans.append(plan)

            end_extensions_init_time = time.time()

            start_time_heappush = time.time()
            for plan in extended_plans:
                heapq.heappush(self.plans_queue, plan)
            end_time_heappush = time.time()

            compute_heurstic_time_delta = self.metrics['plan_compute_heurstic_time_total'] - compute_heurstic_time_before
            self.metrics['extended_plans_initialization_time'] += (end_extensions_init_time-start_extensions_init_time) - compute_heurstic_time_delta
            self.metrics['plans_queue_operations_time'] += (end_time_heappush-start_time_heappush)
            if METRICS_SETTINGS['EXPANSIONS']:
                self.metrics['trasnit_expansions_total'] += len(fastest_ways) - walking_trips_found
                self.metrics['walking_expansions_total'] += walking_trips_found
                self.metrics['expansions_total'] += len(fastest_ways)
                if len(self.plans_queue) > self.metrics['plans_queue_max_size']:
                    self.metrics['plans_queue_max_size'] = len(self.plans_queue)

            start_plan_accepting_time = time.time()

    def is_accepatble_alternative(self, plan, used_trips):
        if not self.found_plans:
            return True

        prev_plan = self.found_plans[-1]
        prev_time = prev_plan.current_time - prev_plan.start_time
        cur_time = plan.current_time - plan.start_time
        settings = ALTERNATIVE_PLAN_SETTINGS

        if cur_time < self.shortest_time:
            self.shortest_time = cur_time

        acceptable_time = (
            cur_time <= self.shortest_time * (1 + settings["ALLOWED_RELATIVE_DIFFERENCE"])
            or
            cur_time <= self.shortest_time + settings["ALLOWED_ABSOLUTE_DIFFERENCE"]
        )

        if prev_plan.start_time >= plan.start_time and not acceptable_time:
            return False

        duplicate = any(used_trips.issuperset(ut) for ut in self.used_trips)
        return not duplicate

    def next_gen(self, plan):
        if not plan.plan_trips:
            return

        stop_id = plan.plan_trips[0].from_stop
        new_time = plan.plan_trips[0].departure_time + 1

        alternative = Plan.initial(
            stop_id,
            new_time - plan.initial_walk,
            plan.initial_walk,
        )

        alternative.generation = plan.generation + 1

        if self.discovered_stops[stop_id].register_plan(alternative):
            alternative.walk_time = self.get_walk_time(stop_id)
            alternative.travel_time = self.get_estimate(stop_id, new_time).travel_time

            t0 = time.time()
            heapq.heappush(self.plans_queue, alternative)
            self.metrics['plans_queue_operations_time'] += time.time() - t0


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
