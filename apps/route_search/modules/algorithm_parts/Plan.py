from .PlanTrip import PlanTrip
from .utils import time_to_seconds, seconds_to_time, get_previous_day, get_next_day
from .DataLoaderSingleton import initialized_dataloader_singleton


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
            arrival_date,
            # date of a last trip in the plan. If the plan spans over midnight, the date may be the next day
            starting_stop_id: int = None,
            plan_trips: list[PlanTrip] = None,
    ):
        if starting_stop_id is None and plan_trips is None:
            raise Exception('either starting_stop_id or plan_trips must be specified')

        if starting_stop_id is not None and start_time is not None:
            # initialization
            self.arrival_date = arrival_date
            self.plan_trips = list()
            self.used_trips = set()
            self.used_stops = set()
            self.current_stop_id = starting_stop_id
            self.start_time = start_time + start_walking_times[starting_stop_id]
            self.current_time = self.start_time
            self.time_at_destination = self.current_time + destination_walking_times[starting_stop_id]
            self.heuristic_time_at_destination = self.current_time + heuristic_times[starting_stop_id]

        if plan_trips is not None:
            # extended plan
            self.arrival_date = arrival_date
            self.start_time = start_time
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

    def get_absolute_arrival_time_difference(self, other):
        """
        returns difference in seconds between arrival times of this and other plan, considering the date
        """
        if self.arrival_date == other.arrival_date:
            difference = self.get_informed_time_at_destination() - other.get_informed_time_at_destination()
        elif self.arrival_date == get_previous_day(other.arrival_date):
            difference = self.get_informed_time_at_destination() - (
                        other.get_informed_time_at_destination() + time_to_seconds('24:00:00'))
        elif self.arrival_date == get_next_day(other.arrival_date):
            difference = self.get_informed_time_at_destination() - (
                        other.get_informed_time_at_destination() - time_to_seconds('24:00:00'))
        else:
            raise ValueError(f"Dates of arrival are too far apart: {self.arrival_date} and {other.arrival_date}")
        return difference

    def __str__(self):
        starting_stop_id = self.current_stop_id if len(self.plan_trips) == 0 else self.plan_trips[0].start_from_stop_id
        stops = initialized_dataloader_singleton.get_stops()
        start = stops[starting_stop_id]
        result = f"start at: {str(start)} on {seconds_to_time(self.start_time)}\n"
        for plan_trip in self.plan_trips:
            result += "\t" + str(plan_trip).replace("\n", "\n\t") + "\n"
        result += f"reach destination at: {seconds_to_time(self.time_at_destination)}"
        return result

    def __repr__(self):
        return f"Plan({';'.join(map(str, [self.plan_trips, self.used_trips, self.current_stop_id, self.current_time, self.time_at_destination]))})"

    def __lt__(self, other):
        return self.get_absolute_arrival_time_difference(other) < 0

    def __le__(self, other):
        return self.get_absolute_arrival_time_difference(other) <= 0

    def __eq__(self, other):
        return self.get_absolute_arrival_time_difference(other) == 0

    def __ne__(self, other):
        return self.get_absolute_arrival_time_difference(other) != 0

    def __gt__(self, other):
        return self.get_absolute_arrival_time_difference(other) > 0

    def __ge__(self, other):
        return self.get_absolute_arrival_time_difference(other) >= 0