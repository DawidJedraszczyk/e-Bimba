import numba as nb
import numba.types as nbt
from numba.experimental import jitclass
import numpy as np
from typing import Iterator, NamedTuple, Optional

from .misc import *


class Trip(NamedTuple):
  route_id: int
  shape_id: int
  headsign: str
  first_departure: int
  last_departure: int
  starts: Range
  stops: Range


class TripStart(NamedTuple):
  service: int
  time: int
  offset: int


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
  ("starts_off", nb.int32[:]),
  ("starts_services_off", nb.int32[:]),
  ("starts_services", nb.int32[:]),
  ("starts_times_off", nb.int32[:]),
  ("starts_times", nb.int32[:]),
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
    starts_off,
    starts_services_off,
    starts_services,
    starts_times_off,
    starts_times,
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
    self.starts_off = starts_off
    self.starts_services_off = starts_services_off
    self.starts_services = starts_services
    self.starts_times_off = starts_times_off
    self.starts_times = starts_times
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
      Range(self.starts_off[id], self.starts_off[id+1]),
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


  def get_next_start(self, trip_id: int, services: Services, earliest: int) -> TripStart:
    starts_end = self.starts_off[trip_id+1]
    starts_beg = self.starts_off[trip_id]
    first_departure = self.first_departures[trip_id]
    last_departure = self.last_departures[trip_id]

    start = self._get_next_start(starts_beg, starts_end, services.today, earliest)

    if earliest <= last_departure - DAY:
      yts = self._get_next_start(starts_beg, starts_end, services.yesterday, earliest + DAY)
      start = _ts_min(start, _ts_offset(yts, -DAY))

    if start.time >= first_departure + DAY:
      tts = self._get_next_start(starts_beg, starts_end, services.tomorrow, earliest - DAY)
      start = _ts_min(start, _ts_offset(tts, DAY))

    return start


  def _get_next_start(self, starts_beg, starts_end, day_services, earliest: int) -> TripStart:
    start = TripStart(nb.int32(-1), nb.int32(INF_TIME), nb.int32(0))

    for starts_i in range(starts_beg, starts_end):
      service = self._common_service(starts_i, day_services)

      if service == -1:
        continue

      times_end = self.starts_times_off[starts_i+1]
      times_beg = self.starts_times_off[starts_i]
      times_i = times_beg + np.searchsorted(self.starts_times[times_beg:times_end], earliest)

      if times_i < times_end and self.starts_times[times_i] < start.time:
        start = TripStart(service, self.starts_times[times_i], nb.int32(0))

    return start


  def _common_service(self, starts_i, day_services):
    starts_service_end = self.starts_services_off[starts_i+1]
    starts_service_i = self.starts_services_off[starts_i]
    day_service_end = len(day_services)
    day_service_i = 0

    while starts_service_i < starts_service_end and day_service_i < day_service_end:
      starts_service_id = self.starts_services[starts_service_i]
      day_service_id = day_services[day_service_i]

      if starts_service_id == day_service_id:
        return starts_service_id
      elif starts_service_id > day_service_id:
        day_service_i += 1
      else:
        starts_service_i += 1

    return nb.int32(-1)


@nb.jit
def _ts_offset(ts, offset):
  return TripStart(ts.service, nb.int32(ts.time + offset), nb.int32(offset))


@nb.jit
def _ts_min(a, b):
  if a.time < b.time:
    return a
  else:
    return b
