from dataclasses import dataclass
from typing import NamedTuple

from .data import Data
from .estimator import Estimates
from .utils import time_to_seconds, seconds_to_time
from transit.prospector import NearStop
from ebus.algorithm_settings import INCONVENIENCE_SETTINGS


class PlanTrip(NamedTuple):
    trip_id: int
    service_id: int
    trip_start: int
    from_stop: int
    departure_time: int
    to_stop: int
    arrival_time: int


@dataclass
class Plan:
    start_time: int
    initial_walk_time: int
    current_stop_id: int
    current_time: int
    inconvenience: int
    estimates: Estimates
    plan_trips: list[PlanTrip]
    generation: int = 0

    # Distinguishes between potential terminal plans from the ones in heuristic stage
    is_terminal: bool = False

    # A better plan was found after adding this one to the queue
    superseded: bool = False

    def __lt__(self, other):
        return self.informed_score < other.informed_score

    # Lower is better
    @property
    def score(self):
        return (self.current_time + self.estimates.travel_time, self.inconvenience)

    @property
    def informed_score(self):
        return (self.get_informed_time_at_destination(), self.inconvenience)

    @property
    def time_at_destination(self):
        return self.current_time + self.estimates.walk_time

    @property
    def first_stop(self):
        return self.current_stop_id if not self.plan_trips else self.plan_trips[0].from_stop

    @staticmethod
    def from_start(start_time: int, walk_time: int, stop_id: int, estimates: Estimates):
        return Plan(
            start_time,
            walk_time,
            stop_id,
            start_time + walk_time,
            walk_time * INCONVENIENCE_SETTINGS["WALK_TIME_PENALTY"],
            estimates,
            [],
        )

    def extend(self, plan_trip: PlanTrip, estimates: Estimates):
        if plan_trip.trip_id == -1 and not self.plan_trips:
            return Plan.from_start(
                self.start_time,
                self.initial_walk_time + plan_trip.arrival_time - plan_trip.departure_time,
                plan_trip.to_stop,
                estimates,
            )

        inconvenience = self.inconvenience

        if plan_trip.trip_id == -1:
            walk_time = plan_trip.arrival_time - plan_trip.departure_time
            inconvenience += walk_time * INCONVENIENCE_SETTINGS["WALK_TIME_PENALTY"]
        elif self.plan_trips:
            inconvenience += INCONVENIENCE_SETTINGS["TRANSFER_PENALTY"]
            wait_time = plan_trip.departure_time - self.plan_trips[-1].arrival_time
            inconvenience += wait_time * INCONVENIENCE_SETTINGS["WAIT_TIME_PENALTY"]

        return Plan(
            self.start_time,
            self.initial_walk_time,
            plan_trip.to_stop,
            plan_trip.arrival_time,
            inconvenience,
            estimates,
            self.plan_trips + [plan_trip],
            self.generation,
        )

    def get_used_trip_instances(self) -> frozenset[tuple[int, int]]:
        return frozenset(
            (pt.trip_id, pt.trip_start)
            for pt in self.plan_trips
            if pt.trip_id != -1
        )

    def set_as_terminal(self):
        self.is_terminal = True

    def get_informed_time_at_destination(self):
        if self.is_terminal:
            return self.current_time + self.estimates.walk_time
        else:
            return self.current_time + self.estimates.travel_time

    def get_absolute_arrival_time_difference(self, other):
        return self.get_informed_time_at_destination() - other.get_informed_time_at_destination()

    def format(self, data: Data):
        if len(self.plan_trips) == 0:
            starting_stop_id = self.current_stop_id
            start_time = self.current_time
        else:
            starting_stop_id = self.plan_trips[0].from_stop
            start_time = self.plan_trips[0].departure_time

        start = data.stops[starting_stop_id]
        result = f"start at: {start.name} ({start.code}) on {seconds_to_time(start_time)}\n"

        for plan_trip in self.plan_trips:
            from_stop = data.stops[plan_trip.from_stop]
            to_stop = data.stops[plan_trip.to_stop]

            result += f"\tget from {from_stop.name} ({from_stop.code})\n"
            if plan_trip.trip_id == -1:
                result += f"\t\t BY FOOT ([{seconds_to_time(plan_trip.departure_time)}] - [{seconds_to_time(plan_trip.arrival_time)}])\n"
            else:
                route_id = data.trips[plan_trip.trip_id].route_id
                route_name = data.routes[route_id].name
                result += f"\t\t USING {route_name} ([{seconds_to_time(plan_trip.departure_time)}] - [{seconds_to_time(plan_trip.arrival_time)}])\n"
            result += f"\tto {to_stop.name} ({to_stop.code})\n"

        time_at_destination = self.get_informed_time_at_destination()
        result += f"reach destination at: {seconds_to_time(time_at_destination)}\n"
        result += f"inconvenience: {self.inconvenience}"
        return result
