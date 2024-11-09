import numba as nb
import numba.types as nbt
from numba.experimental import jitclass
import numpy as np
from typing import Iterator, NamedTuple, Optional

from .common import *


class Trip(NamedTuple):
  route_id: int
  shape_id: int
  headsign: str
  first_departure: int
  last_departure: int
  instances: Range
  stops: Range


class TripInstance(NamedTuple):
  services: Range
  start_times: Range


class TripStop(NamedTuple):
  stop_id: int
  arrival: int
  departure: int


@jitclass([
  ("routes", nb.int32[:]),
  ("shapes", nb.int32[:]),
  ("headsigns", nbt.List(nbt.string)),
  ("first_departures", nb.int32[:]),
  ("last_departures", nb.int32[:]),
  ("instances_off", nb.int32[:]),
  ("instances_services_off", nb.int32[:]),
  ("instances_services", nb.int32[:]),
  ("instances_start_times_off", nb.int32[:]),
  ("instances_start_times", nb.int32[:]),
  ("stops_off", nb.int32[:]),
  ("stops_ids", nb.int32[:]),
  ("stops_arrivals", nb.int32[:]),
  ("stops_departures", nb.int32[:]),
])
class Trips:
  def __init__(
    self,
    routes,
    shapes,
    headsigns,
    first_departures,
    last_departures,
    instances_off,
    instances_services_off,
    instances_services,
    instances_start_times_off,
    instances_start_times,
    stops_off,
    stops_ids,
    stops_arrivals,
    stops_departures,
  ):
    self.routes = routes
    self.shapes = shapes
    self.headsigns = headsigns
    self.first_departures = first_departures
    self.last_departures = last_departures
    self.instances_off = instances_off
    self.instances_services_off = instances_services_off
    self.instances_services = instances_services
    self.instances_start_times_off = instances_start_times_off
    self.instances_start_times = instances_start_times
    self.stops_off = stops_off
    self.stops_ids = stops_ids
    self.stops_arrivals = stops_arrivals
    self.stops_departures = stops_departures


  def __getitem__(self, id: int) -> Trip:
    return Trip(
      self.routes[id],
      self.shapes[id],
      self.headsigns[id],
      self.first_departures[id],
      self.last_departures[id],
      Range(self.instances_off[id], self.instances_off[id+1]),
      Range(self.stops_off[id], self.stops_off[id+1]),
    )


  def get_trip(self, id: int) -> Trip:
    return self[id]


  def get_trip_stops(self, trip_id: int) -> list[TripStop]:
    end = self.stops_off[trip_id+1]
    beg = self.stops_off[trip_id]

    return [
      TripStop(self.stops_ids[i], self.stops_arrivals[i], self.stops_departures[i])
      for i in range(beg, end)
    ]


  def get_stops_after(self, trip_id: int, seq: int) -> Iterator[TripStop]:
    end = self.stops_off[trip_id+1]
    beg = self.stops_off[trip_id] + seq + 1

    for i in range(beg, end):
      yield TripStop(
        self.stops_ids[i],
        self.stops_arrivals[i],
        self.stops_departures[i],
      )


  def get_next_start(self, trip_id: int, services: Services, time: int) -> int:
    i_end = self.instances_off[trip_id+1]
    i_beg = self.instances_off[trip_id]
    first_departure = self.first_departures[trip_id]
    last_departure = self.last_departures[trip_id]

    start_time = self._get_next_start(i_beg, i_end, services.today, time)

    if time <= last_departure - DAY:
      st = self._get_next_start(i_beg, i_end, services.yesterday, time + DAY) - DAY
      start_time = min(start_time, st)

    if start_time >= first_departure + DAY:
      st = self._get_next_start(i_beg, i_end, services.tomorrow, time - DAY) + DAY
      start_time = min(start_time, st)

    return start_time


  def _get_next_start(self, i_beg, i_end, day_services, time: int) -> int:
    start_time = nb.int32(INF_TIME)

    for instance in range(i_beg, i_end):
      if not self._instance_and_day_have_common_service(instance, day_services):
        continue

      times_end = self.instances_start_times_off[instance+1]
      times_beg = self.instances_start_times_off[instance]
      times_i = times_beg + np.searchsorted(self.instances_start_times[times_beg:times_end], time)

      if times_i < times_end:
        start_time = min(start_time, self.instances_start_times[times_i])

    return start_time


  def _instance_and_day_have_common_service(self, instance, day_services):
    instance_service_end = self.instances_services_off[instance+1]
    instance_service_i = self.instances_services_off[instance]
    day_service_end = len(day_services)
    day_service_i = 0

    while instance_service_i < instance_service_end and day_service_i < day_service_end:
      is_id = self.instances_services[instance_service_i]
      id_id = day_services[day_service_i]

      if is_id == id_id:
        return True
      elif is_id > id_id:
        day_service_i += 1
      else:
        instance_service_i += 1

    return False
