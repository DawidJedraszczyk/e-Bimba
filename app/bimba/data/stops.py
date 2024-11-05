import numba as nb
import numba.types as nbt
from numba.experimental import jitclass
from typing import Iterator, NamedTuple, Optional

from .common import *


class Stop(NamedTuple):
  code: Optional[str]
  name: str
  zone: Optional[str]
  coords: Coords
  walks: Range
  trips: Range


class StopWalk(NamedTuple):
  stop_id: int
  distance: int


class StopTrip(NamedTuple):
  trip_id: int
  seq: int
  departure: int


@jitclass([
  ("codes", nbt.List(nbt.string)),
  ("names", nbt.List(nbt.string)),
  ("zones", nbt.List(nbt.string)),
  ("lats", nb.float32[:]),
  ("lons", nb.float32[:]),
  ("walks_off", nb.int32[:]),
  ("walks_stop_ids", nb.int32[:]),
  ("walks_distances", nb.int16[:]),
  ("trips_off", nb.int32[:]),
  ("trips_ids", nb.int32[:]),
  ("trips_seqs", nb.int16[:]),
  ("trips_departures", nb.int32[:]),
])
class Stops:
  def __init__(
    self,
    codes,
    names,
    zones,
    lats,
    lons,
    walks_off,
    walks_stop_ids,
    walks_distances,
    trips_off,
    trips_ids,
    trips_seqs,
    trips_departures,
  ):
    self.codes = codes
    self.names = names
    self.zones = zones
    self.lats = lats
    self.lons = lons
    self.walks_off = walks_off
    self.walks_stop_ids = walks_stop_ids
    self.walks_distances = walks_distances
    self.trips_off = trips_off
    self.trips_ids = trips_ids
    self.trips_seqs = trips_seqs
    self.trips_departures = trips_departures

  def get_stop(self, id: int) -> Stop:
    return Stop(
      self.codes[id],
      self.names[id],
      self.zones[id],
      Coords(self.lats[id], self.lons[id]),
      Range(self.walks_off[id], self.walks_off[id+1]),
      Range(self.trips_off[id], self.trips_off[id+1]),
    )

  def get_stop_walks(self, id) -> Iterator[StopWalk]:
    return self.get_walks(Range(self.walks_off[id], self.walks_off[id+1]))

  def get_stop_trips(self, id) -> Iterator[StopTrip]:
    return self.get_trips(Range(self.trips_off[id], self.trips_off[id+1]))

  def get_walks(self, walks: Range) -> Iterator[StopWalk]:
    for i in range(walks.beg, walks.end):
      yield StopWalk(
        self.walks_stop_ids[i],
        self.walks_distances[i],
      )

  def get_trips(self, trips: Range) -> Iterator[StopTrip]:
    for i in range(trips.beg, trips.end):
      yield StopTrip(
        self.trips_ids[i],
        self.trips_seqs[i],
        self.trips_departures[i],
      )
