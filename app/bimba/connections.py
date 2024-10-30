import numba as nb # type: ignore
from numba.experimental import jitclass # type: ignore
import numpy as np
import pyarrow
from typing import Optional


@jitclass([
  ("departure", nb.int32),
  ("arrival", nb.int32),
  ("id", nb.int32),
])
class Trip:
  def __init__(self, departure, arrival, id):
    self.departure = departure
    self.arrival = arrival
    self.id = id

  def __str__(self):
    return f"({self.departure}, {self.arrival}, {self.id})"


@jitclass([
  ("start", nb.int32),
  ("end", nb.int32),
])
class Services:
  def __init__(self, start, end):
    self.start = start
    self.end = end

  def __str__(self):
    return f"{self.start} .. {self.end}"

  def __getitem__(self, i: int):
    return self.start + i

  def len(self):
    return self.end - self.start


@jitclass([
  ("to_stop", nb.int32),
  ("walk_time", nb.int16),
  ("first_arrival", nb.int32),
  ("last_departure", nb.int32),
  ("services", Services.class_type.instance_type), # type: ignore
])
class Connection:
  def __init__(self, to_stop, walk_time, first_arrival, last_departure, services):
    self.to_stop = to_stop
    self.walk_time = walk_time
    self.first_arrival = first_arrival
    self.last_departure = last_departure
    self.services = services

  def __str__(self):
    return f"({self.to_stop}, {self.walk_time}, {self.first_arrival}, {self.last_departure}, {self.services})"


@jitclass([
  ("to_stops_off", nb.int32[:]),
  ("to_stop", nb.int32[:]),
  ("walk_time", nb.int16[:]),
  ("first_arrival", nb.int32[:]),
  ("last_departure", nb.int32[:]),
  ("services_off", nb.int32[:]),
  ("service_off", nb.int32[:]),
  ("departures", nb.int32[:]),
  ("arrivals", nb.int32[:]),
  ("trip_ids", nb.int32[:]),
])
class Connections:
  def __init__(
    self,
    to_stops_off,
    to_stop,
    walk_time,
    first_arrival,
    last_departure,
    services_off,
    service_off,
    departures,
    arrivals,
    trip_ids,
  ):
    self.to_stops_off = to_stops_off
    self.to_stop = to_stop
    self.walk_time = walk_time
    self.first_arrival = first_arrival
    self.last_departure = last_departure
    self.services_off = services_off
    self.service_off = service_off
    self.departures = departures
    self.arrivals = arrivals
    self.trip_ids = trip_ids

  def from_stop(self, id: int):
    start = self.to_stops_off[id]
    end = self.to_stops_off[id+1]

    for i in range(start, end):
      yield Connection(
        self.to_stop[i],
        self.walk_time[i],
        self.first_arrival[i],
        self.last_departure[i],
        Services(
          self.services_off[i],
          self.services_off[i+1],
        ),
      )

  def find_trip(self, service: int, after: int) -> Optional[Trip]:
    start = self.service_off[service]
    end = self.service_off[service + 1]
    i = start + np.searchsorted(self.departures[start:end], after)

    if i == end:
      return None
    else:
      return Trip(
        self.departures[i],
        self.arrivals[i],
        self.trip_ids[i],
      )



def connections_from_arrow(cs: pyarrow.ListArray) -> Connections:
  to_stops_off = cs.offsets
  to_stop, walk_time, first_arrival, last_departure, services = cs.values.flatten() # type: ignore
  services_off = services.offsets
  service = services.values
  service_off = service.offsets
  departures, arrivals, trip_ids = service.values.flatten()

  return Connections(
    to_stops_off.to_numpy(),
    to_stop.to_numpy(),
    walk_time.to_numpy(),
    first_arrival.to_numpy(),
    last_departure.to_numpy(),
    services_off.to_numpy(),
    service_off.to_numpy(),
    departures.to_numpy(),
    arrivals.to_numpy(),
    trip_ids.to_numpy(),
  )
