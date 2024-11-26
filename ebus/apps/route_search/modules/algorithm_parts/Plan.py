from dataclasses import dataclass

from .data import Data
from .estimator import Estimates
from .PlanTrip import PlanTrip
from .inconvenience import inconvenience
from .utils import time_to_seconds, seconds_to_time
from bimba.prospector import NearStop
from ebus.algorithm_settings import INCONVENIENCE_SETTINGS


@dataclass
class Plan:
    current_stop_id: int
    current_time: int
    estimates: Estimates
    plan_trips: list[PlanTrip]
    inconvenience: int

    # Distinguishes between potential terminal plans from the ones in heuristic stage
    is_terminal: bool = False

    @property
    def time_at_destination(self):
        return self.current_time + self.estimates.walk_time

    @staticmethod
    def from_start(start_time: int, stop_id: int, walk_time: int, estimates: Estimates):
        return Plan(
            stop_id,
            start_time + walk_time,
            estimates,
            [],
            walk_time * INCONVENIENCE_SETTINGS["WALK_TIME_PENALTY"],
        )

    def extend(self, plan_trip: PlanTrip, estimates: Estimates):
        inconvenience = self.inconvenience

        if plan_trip.trip_id == -1:
            walk_time = plan_trip.arrival_time - plan_trip.departure_time
            inconvenience += walk_time * INCONVENIENCE_SETTINGS["WALK_TIME_PENALTY"]
        elif len(self.plan_trips) > 1:
            # Transferring between trams is inconvenient
            inconvenience += INCONVENIENCE_SETTINGS["TRANSFER_PENALTY"]

            wait_time = plan_trip.departure_time - self.plan_trips[-1].arrival_time
            inconvenience += wait_time * INCONVENIENCE_SETTINGS["WAIT_TIME_PENALTY"]

        return Plan(
            plan_trip.to_stop,
            plan_trip.arrival_time,
            estimates,
            self.plan_trips + [plan_trip],
            inconvenience
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
            result += "\t" + plan_trip.format(data).replace("\n", "\n\t") + "\n"

        time_at_destination = self.get_informed_time_at_destination()
        result += f"reach destination at: {seconds_to_time(time_at_destination)}"
        return result

    def __lt__(self, other):
        self_val = (self.get_informed_time_at_destination(), self.inconvenience)
        other_val = (other.get_informed_time_at_destination(), other.inconvenience)
        return self_val < other_val
