from typing import NamedTuple
from .data import Data
from .utils import seconds_to_time


class PlanTrip(NamedTuple):
    trip_id: int
    service_id: int
    trip_start: int
    start_from_stop_id: int
    departure_time: int
    leave_at_stop_id: int
    arrival_time: int

    def __str__(self):
        data = Data.instance()
        start = data.stops[self.start_from_stop_id]
        leave = data.stops[self.leave_at_stop_id]

        result = f"get from {start.name} ({start.code})\n"
        if self.trip_id == -1:
            result += f"\t BY FOOT ([{seconds_to_time(self.departure_time)}] - [{seconds_to_time(self.arrival_time)}])\n"
        else:
            route_id = data.trips[self.trip_id].route_id
            route_name = data.routes[route_id].name
            result += f"\t USING {route_name} ([{seconds_to_time(self.departure_time)}] - [{seconds_to_time(self.arrival_time)}])\n"
        result += f"to {leave.name} ({leave.code})"
        return result

    def __repr__(self):
        return f"""PlanTrip({';'.join(map(str, [
            self.trip_id, self.start_from_stop_id,
            self.departure_time, self.leave_at_stop_id, self.arrival_time,
        ]))})"""
