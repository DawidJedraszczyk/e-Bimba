import numpy as np
import numba as nb
from numba.experimental import jitclass
import numba.types as nbt
from typing import NamedTuple


DAY = 24*60*60
INF_TIME = 0x1FFFFFFF


class Point(NamedTuple):
  x: np.float32
  y: np.float32

  def distance(self, other) -> np.float32:
    return np.sqrt((self.x - other.x)**2 + (self.y-other.y)**2)


class Coords(NamedTuple):
  lat: np.float32
  lon: np.float32

class Range(NamedTuple):
  beg: int
  end: int


class TripInstance(NamedTuple):
  wheelchair_accessible: int
  gtfs_trip_id: str


class Metadata(NamedTuple):
  name: str
  region: str
  projection: str
  center_coords: Coords
  center_position: Point
  realtime: list[str]


@jitclass([
  ("today", nb.int32[:]),
  ("yesterday", nb.int32[:]),
  ("tomorrow", nb.int32[:]),
])
class Services:
  def __init__(self, today, yesterday, tomorrow):
    self.today = today
    self.yesterday = yesterday
    self.tomorrow = tomorrow

    self.today.sort()
    self.yesterday.sort()
    self.tomorrow.sort()

  @staticmethod
  def empty():
    return Services(
      np.empty(0, np.int32),
      np.empty(0, np.int32),
      np.empty(0, np.int32),
    )


@jitclass([
  ("dict", nbt.DictType(nbt.UniTuple(nb.int32, 3), nb.int32)),
])
class Delays:
  def __init__(self, trip_ids, services, start_times, delays):
    self.dict = dict(
      zip(
        zip(trip_ids, services, start_times),
        delays,
      )
    )

  def __getitem__(self, trip_triple):
    delay = self.dict.get(trip_triple)

    if delay is None:
      return nb.int32(0)
    else:
      return delay

  @staticmethod
  def empty():
    return Delays(
      np.empty(0, np.int32),
      np.empty(0, np.int32),
      np.empty(0, np.int32),
      np.empty(0, np.int32),
    )


NbtPoint = nbt.NamedUniTuple(nb.float32, 2, Point)
NbtCoords = nbt.NamedUniTuple(nb.float32, 2, Coords)
