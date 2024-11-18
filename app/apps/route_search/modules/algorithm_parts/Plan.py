from .data import Data
from .PlanTrip import PlanTrip
from .inconvenience import inconvenience
from .utils import time_to_seconds, seconds_to_time


class Plan():
    # FIXME - modify to initalize once and include method to return extended plan of that plan
    # then modify how the extended plan is made in AstarPlanner
    """
    `starting_stop_id` is used for initialization of A*                           \n
    - it is the stop_id's of stops within walking distance of start location      \n
    - should be `None` in further usage after initialization, when instead, we're
      building Plans by extending current ones                                    \n

    `plan_trips` is used after initialization of A*                               \n
    - it is the `PlanTrip`s explored between start and destination                \n
    - should be `None` in initialization, when we're just starting to build Plans
    """

    def __init__(
            self,
            start_walking_times,
            destination_walking_times,
            heuristic_times,
            start_time,  # start time of the plan (used only for initialization)
            # date of a last trip in the plan. If the plan spans over midnight, the date may be the next day
            starting_stop_id: int = None,
            plan_trips: list[PlanTrip] = None,
            prev_inconvenience = 0,
    ):
        if starting_stop_id is None and plan_trips is None:
            raise Exception('either starting_stop_id or plan_trips must be specified')
        
        self.heuristic_times = heuristic_times
        self.destination_walking_times = destination_walking_times
        self.heuristic_time_at_destination = None
        self.time_at_destination = None

        if starting_stop_id is not None and start_time is not None:
            walk_time = int(start_walking_times[starting_stop_id])
            # initialization
            self.plan_trips = list()
            self.used_trips = {-1} # numba can't handle an empty set
            self.used_stops = {starting_stop_id}
            self.current_stop_id = starting_stop_id
            self.start_time = start_time + walk_time
            self.current_time = self.start_time
            self.inconvenience = inconvenience(walk_time=walk_time)

        if plan_trips is not None:
            # extended plan
            self.start_time = start_time
            self.plan_trips = plan_trips
            self.used_trips = {plan_trip.trip_id for plan_trip in plan_trips}
            self.used_stops = {plan_trip.start_from_stop_id for plan_trip in plan_trips}
            self.last_plan_trip = plan_trips[-1]
            self.current_stop_id = self.last_plan_trip.leave_at_stop_id
            self.current_time = self.last_plan_trip.arrival_time

            if plan_trips[-1].trip_id == -1:
                wait_time = None
                walk_time = plan_trips[-1].arrival_time - plan_trips[-1].departure_time
            elif len(plan_trips) > 1:
                wait_time = plan_trips[-1].departure_time - plan_trips[-2].arrival_time
                walk_time = None
            else:
                wait_time = None
                walk_time = None

            self.inconvenience = prev_inconvenience + inconvenience(
                transfer=(len(self.used_stops) > 2 and plan_trips[-1].trip_id != -1),
                wait_time=wait_time,
                walk_time=walk_time,
            )

        # simple flag that distinguishes between potential terminal plans from ones in heuristic stage
        self.is_terminal = False

    def compute_heuristic_time_at_destination(self):
        if not self.plan_trips:
            self.heuristic_time_at_destination = self.current_time + self.heuristic_times[self.current_stop_id]
        else:
            self.heuristic_time_at_destination = self.last_plan_trip.arrival_time + self.heuristic_times[self.current_stop_id]
    
    def __compute_actual_time_at_destination(self):
        if not self.plan_trips:
            self.time_at_destination = self.current_time + self.destination_walking_times[self.current_stop_id]
        else:
            self.time_at_destination = self.last_plan_trip.arrival_time + self.destination_walking_times[self.current_stop_id]

    def set_as_terminal(self):
        self.__compute_actual_time_at_destination()
        self.is_terminal = True

    def get_informed_time_at_destination(self):
        """Gets time at destination, taking into account if plan is terminal"""
        if self.heuristic_time_at_destination is None:
            raise Exception('heuristic_time_at_destination must be computed first')
        if self.is_terminal and self.time_at_destination is None:
            raise Exception('time_at_destination must be computed first')
        return self.time_at_destination if self.is_terminal else self.heuristic_time_at_destination

    def get_absolute_arrival_time_difference(self, other):
        return self.get_informed_time_at_destination() - other.get_informed_time_at_destination()

    def format(self, data: Data):
        starting_stop_id = self.current_stop_id if len(self.plan_trips) == 0 else self.plan_trips[0].start_from_stop_id
        start = data.stops[starting_stop_id]
        result = f"start at: {start.name} ({start.code}) on {seconds_to_time(self.start_time)}\n"
        for plan_trip in self.plan_trips:
            result += "\t" + plan_trip.format(data).replace("\n", "\n\t") + "\n"
        self.__compute_actual_time_at_destination()
        result += f"reach destination at: {seconds_to_time(self.time_at_destination)}"
        return result

    def __repr__(self):
        return f"Plan({';'.join(map(str, [self.plan_trips, self.used_trips, self.current_stop_id, self.current_time, self.time_at_destination]))})"

    def __lt__(self, other):
        self_val = (self.get_informed_time_at_destination(), self.inconvenience)
        other_val = (other.get_informed_time_at_destination(), other.inconvenience)
        return self_val < other_val
