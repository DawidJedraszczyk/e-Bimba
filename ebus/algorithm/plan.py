from dataclasses import dataclass
from typing import NamedTuple

from .data import Data
from .estimator import Estimate
from .utils import time_to_seconds, seconds_to_time
from transit.data.misc import INF_TIME
from transit.prospector import NearStop
from ebus.algorithm_settings import INCONVENIENCE_SETTINGS


class PlanTrip(NamedTuple):
    from_stop: int # -1 if from start
    departure_time: int
    to_stop: int
    arrival_time: int

    # All -1 if walking
    trip_id: int = -1
    service_id: int = -1
    trip_start: int = -1


@dataclass
class Plan:
    current_stop_id: int
    current_time: int
    inconvenience: int
    initial_walk: int
    plan_trips: list[PlanTrip]
    generation: int = 0
    travel_time: int = INF_TIME
    walk_time: int = INF_TIME

    # A better plan was found after adding this one to the queue
    superseded: bool = False

    def __lt__(self, other):
        return self.score < other.score

    # Lower is better
    @property
    def score(self):
        return (self.current_time + self.travel_time, self.inconvenience)

    @property
    def stop_score(self):
        return (self.current_time, self.inconvenience)

    @property
    def time_at_destination(self):
        return self.current_time + self.walk_time

    @property
    def start_time(self):
        if self.plan_trips:
            return self.plan_trips[0].departure_time - self.initial_walk
        else:
            return self.current_time - self.initial_walk

    @staticmethod
    def initial(stop_id, start_time, initial_walk):
        return Plan(
            stop_id,
            start_time + initial_walk,
            int(initial_walk * INCONVENIENCE_SETTINGS["WALK_TIME_PENALTY"]),
            initial_walk,
            [],
        )

    def extend(self, plan_trip: PlanTrip):
        if plan_trip.trip_id == -1 and not self.plan_trips:
            return Plan.initial(
                plan_trip.to_stop,
                self.current_time - self.initial_walk,
                plan_trip.arrival_time - plan_trip.departure_time + self.initial_walk,
            )

        inconvenience = self.inconvenience

        if plan_trip.trip_id == -1:
            walk_time = plan_trip.arrival_time - plan_trip.departure_time
            inconvenience += int(walk_time * INCONVENIENCE_SETTINGS["WALK_TIME_PENALTY"])
        elif self.plan_trips:
            inconvenience += INCONVENIENCE_SETTINGS["TRANSFER_PENALTY"]
            wait_time = plan_trip.departure_time - self.plan_trips[-1].arrival_time
            inconvenience += int(wait_time * INCONVENIENCE_SETTINGS["WAIT_TIME_PENALTY"])

        return Plan(
            plan_trip.to_stop,
            plan_trip.arrival_time,
            inconvenience,
            self.initial_walk,
            self.plan_trips + [plan_trip],
            self.generation,
        )

    def extend_to_destination(self):
        return Plan(
            self.current_stop_id,
            self.current_time + self.walk_time,
            self.inconvenience + self.walk_time * INCONVENIENCE_SETTINGS["WALK_TIME_PENALTY"],
            self.initial_walk,
            self.plan_trips,
            self.generation,
            travel_time=0,
            walk_time=0,
        )

    def get_used_trip_instances(self) -> frozenset[tuple[int, int]]:
        return frozenset(
            (pt.trip_id, pt.trip_start)
            for pt in self.plan_trips
            if pt.trip_id != -1
        )

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

        result += f"reach destination at: {seconds_to_time(self.current_time)}\n"
        result += f"inconvenience: {self.inconvenience}"
        return result
