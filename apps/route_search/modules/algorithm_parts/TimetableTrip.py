import numpy as np


class TimetableTrip:
    def __init__(self, trip_id: str, trip_group, service_id: int):
        self.trip_id = trip_id
        self.service_id = service_id  # identifier of callendar daytype
        self.stop_ids = np.array(trip_group[
                                     'stop_id'])  # simplicity, assume in order (stop_sequence) WHICH IS THE CASE (but implement check in app?)
        self.arrival_times_s = np.array(trip_group['arrival_time_s'])
        self.departure_times_s = np.array(trip_group['departure_time_s'])
        # route_id not needed for algo

    def __str__(self):
        return f"Trip(\ntrip_id={self.trip_id},\nroute_id={self.route_id},\nstop_ids={self.stop_ids},\narrival_times_seconds={self.arrival_times_seconds},\ndeparture_times_seconds={self.departure_times_seconds},\n)"