from algorithm_parts.DataLoaderSingleton import initialized_dataloader_singleton
from algorithm_parts.utils import seconds_to_time


class PlanTrip:
    def __init__(
            self,
            start_from_stop_id, departure_time,
            leave_at_stop_id, arrival_time, type, date, trip_id=None
    ):
        self.type = type  # bus/walking/train/bike/car
        # if it is bus trip,
        if type == 'bus' and trip_id is None:
            raise ValueError("trip_id must be provided for bus trips")
        self.trip_id = trip_id
        self.departure_time = departure_time
        self.arrival_time = arrival_time
        # Those two are also needed to be modified when we start to consider bicycles,
        # because the trips may no longer start or finish at the bus stops
        self.start_from_stop_id = start_from_stop_id
        self.leave_at_stop_id = leave_at_stop_id
        self.date = date

    def __str__(self):
        stops = initialized_dataloader_singleton.get_stops()
        start = stops[self.start_from_stop_id]
        leave = stops[self.leave_at_stop_id]

        result = f"get from {str(start)}\n"
        if self.type == 'WALK':
            result += f"\t BY FOOT ([{seconds_to_time(self.departure_time)}] - [{seconds_to_time(self.arrival_time)}])\n"
        else:
            trips_df = initialized_dataloader_singleton.get_trips_df()
            trip_from_df = trips_df.loc[self.trip_id]
            result += f"\t USING {trip_from_df['route_id']} ([{seconds_to_time(self.departure_time)}] - [{seconds_to_time(self.arrival_time)}])\n"
        result += f"to {str(leave)}"
        return result

    def __repr__(self):
        return f"PlanTrip({';'.join(map(str, [self.type, self.trip_id, self.start_from_stop_id, self.departure_time, self.leave_at_stop_id, self.arrival_time]))})"