from typing import NamedTuple
from .data import Data
from .utils import seconds_to_time


class PlanTrip(NamedTuple):
    trip_id: int
    service_id: int
    trip_start: int
    from_stop: int
    departure_time: int
    to_stop: int
    arrival_time: int

    def format(self, data: Data):
        start = data.stops[self.from_stop]
        leave = data.stops[self.to_stop]

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
            self.trip_id, self.from_stop,
            self.departure_time, self.to_stop, self.arrival_time,
        ]))})"""
