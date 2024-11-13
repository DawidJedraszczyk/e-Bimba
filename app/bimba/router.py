import asyncio
import cProfile
from dataclasses import dataclass
import datetime
from haversine.haversine import get_avg_earth_radius, _haversine_kernel, Unit # type: ignore
import heapq
from itertools import chain
import numba as nb # type: ignore
from numba.experimental import jitclass # type: ignore
import numba.types as nbt
import pyarrow
import time as timer
from typing import NamedTuple, Optional

from .data.common import *
from .data.stops import Stops
from .data.trips import Trips
from .osrm import *
from .params import *
from .transitdb import *


class PathSegment(NamedTuple):
  from_stop: int
  trip_id: int
  details: int # departure if trip_id != -1, walk distance otherwise


class Plan(NamedTuple):
  arrival: int
  path: list[PathSegment]


class Router:
  tdb: TransitDb
  osrm: OsrmClient
  debug: bool
  max_stop_id: int
  stop_coords: NDArray
  stops: Stops
  trips: Trips

  def __init__(self, tdb: TransitDb, osrm: OsrmClient, debug: bool = False):
    self.tdb = tdb
    self.osrm = osrm
    self.debug = debug
    self.max_stop_id = tdb.sql("select max(id) from stop").scalar()
    self.stop_coords = get_stop_coords(self.max_stop_id, tdb)
    self.stops = tdb.get_stops()
    self.trips = tdb.get_trips()

  async def find_route(
      self,
      from_lat: float,
      from_lon: float,
      to_lat: float,
      to_lon: float,
      date: datetime.date,
      time: datetime.time,
  ) -> Plan:
    if self.debug:
      print(f"Routing ({from_lat}, {from_lon}) -> ({to_lat}, {to_lon}) on {date} {time}")

    start_time = time.hour * 60*60 + time.minute * 60 + time.second
    services = self.tdb.get_services(date)
    from_stops = self.tdb.nearest_stops(from_lat, from_lon)
    to_stops = self.tdb.nearest_stops(to_lat, to_lon)

    walks_from, walks_to = await asyncio.gather(
      self.osrm.distance_to_many(
        from_lat, from_lon,
        chain(stop_coords(from_stops), [(to_lat, to_lon)]),
      ),
      self.osrm.distance_to_many(
        to_lat, to_lon,
        stop_coords(to_stops),
      ),
    )

    walk_distance = walks_from[-1]

    if self.debug:
      print(f"  {start_time=}")
      print(f"  {services=}")
      print(f"  {walk_distance=}")
      print(f"  from: {list(zip(stop_ids(from_stops), walks_from))}")
      print(f"  to: {list(zip(stop_ids(to_stops), walks_to))}")

    return RouterTask(
      self.debug,
      self.stop_coords.astype(np.float32),
      self.stops,
      self.trips,
      services,
      NearStops(stop_ids(from_stops), stop_coords(from_stops), walks_from[:-1]),
      NearStops(stop_ids(to_stops), stop_coords(to_stops), walks_to),
      walk_distance,
      start_time,
    ).solve()


_NB_PATH_SEGMENT_TYPE = nbt.NamedUniTuple(nb.int32, 3, PathSegment)

@nb.jit
def empty_segment():
  return PathSegment(nb.int32(-1), nb.int32(-1), nb.int32(-1))


_EARTH_RADIUS = get_avg_earth_radius(Unit.METERS)

@nb.jit
def nb_haversine(a_lat, a_lon, b_lat, b_lon):
  return _EARTH_RADIUS * _haversine_kernel(a_lat, a_lon, b_lat, b_lon)


@jitclass([
  ("stop_id", nb.int32),
  ("estimate", nb.int32),
  ("arrival", nb.int32),
  ("destination_arrival", nb.int32),
  ("walk_distance", nb.int32), # to destination, -1 if too far
  ("path_tail", _NB_PATH_SEGMENT_TYPE),
  ("trip_count", nb.int32),
  ("is_candidate", nb.boolean),
])
class Node:
  def __init__(
    self,
    stop_id: int,
    estimate: int,
    walk_distance: int,
  ):
    self.stop_id = stop_id
    self.estimate = estimate
    self.arrival = INF_TIME
    self.destination_arrival = INF_TIME
    self.walk_distance = walk_distance
    self.path_tail = empty_segment()
    self.trip_count = 0
    self.is_candidate = False

  def __lt__(self, other):
    return self.destination_arrival < other.destination_arrival


@jitclass([
  ("ids", nb.int32[:]),
  ("coords", nb.float32[:, :]),
  ("distances", nb.float32[:]),
])
class NearStops:
  def __init__(self, ids, coords, distances):
    self.ids = ids
    self.coords = coords.astype(np.float32)
    self.distances = distances.astype(np.float32)


_NB_NODE_TYPE = Node.class_type.instance_type

@jitclass([
  ("debug", nb.boolean),
  ("stop_coords", nb.float32[:, :]),
  ("stops", Stops.class_type.instance_type),
  ("trips", Trips.class_type.instance_type),
  ("services", Services.class_type.instance_type),
  ("to_stops", NearStops.class_type.instance_type),

  ("arrival", nb.int32),
  ("path_tail", _NB_PATH_SEGMENT_TYPE),
  ("improved", nb.boolean),

  ("nodes", nbt.DictType(nb.int32, _NB_NODE_TYPE)),
  ("candidates", nbt.ListType(_NB_NODE_TYPE)),

  ("any_improved", nb.boolean),
  ("new_candidates", nbt.ListType(_NB_NODE_TYPE)),
  ("arrival_to_beat", nb.int32),
  ("iteration", nb.int32),
])
class RouterTask:
  def __init__(
    self,
    debug: bool,
    stop_coords: NDArray,
    stops: Stops,
    trips: Trips,
    services: Services,
    from_stops: NearStops,
    to_stops: NearStops,
    walk_distance: float,
    start_time: int,
  ):
    self.debug = debug
    self.stop_coords = stop_coords
    self.stops = stops
    self.trips = trips
    self.services = services
    self.to_stops = to_stops

    self.improved = False
    self.arrival = start_time + int(walk_distance / WALK_SPEED)
    self.path_tail = PathSegment(nb.int32(-1), nb.int32(-1), nb.int32(walk_distance))

    self.nodes = nb.typed.Dict.empty(nb.int32, _NB_NODE_TYPE)
    self.candidates = nb.typed.List.empty_list(_NB_NODE_TYPE)
    self.any_improved = False
    self.new_candidates = nb.typed.List.empty_list(_NB_NODE_TYPE)
    self.arrival_to_beat = INF_TIME
    self.iteration = 0

    for id, dst in zip(to_stops.ids, to_stops.distances):
      self.nodes[id] = Node(id, int(dst / WALK_SPEED), int(dst))

    for id, dst in zip(from_stops.ids, from_stops.distances):
      n = self.get_node(id)
      arrival = start_time + int(dst / WALK_SPEED)
      n.arrival = arrival
      n.destination_arrival = arrival + n.estimate
      n.path_tail = PathSegment(nb.int32(-1), nb.int32(-1), nb.int32(dst))
      n.is_candidate = True
      self.candidates.append(n)

    heapq.heapify(self.candidates)


  def get_node(self, stop_id: int) -> Node:
    node = self.nodes.get(stop_id, None)

    if node is None:
      node = Node(stop_id, self.estimate(stop_id), -1)
      self.nodes[stop_id] = node

    return node


  def estimate(self, stop_id: int) -> int:
    coords = self.stop_coords[stop_id]
    result = INF_TIME

    for target_coords, target_walk in zip(self.to_stops.coords, self.to_stops.distances):
      distance = nb_haversine(coords[0], coords[1], target_coords[0], target_coords[1])
      result = min(result, int(distance / TRAM_SPEED + target_walk / WALK_SPEED))

    return result


  def update_node(self, node: Node, arrival: int, came_from: Node, trip_id: int, details: int):
    destination_arrival = arrival + node.estimate

    if destination_arrival >= self.arrival:
      return

    node.arrival = arrival
    node.destination_arrival = destination_arrival
    node.trip_count = came_from.trip_count + (trip_id != -1)
    node.path_tail = PathSegment(came_from.stop_id, nb.int32(trip_id), nb.int32(details))

    if node.is_candidate:
      self.any_improved = True
    else:
      self.new_candidates.append(node)

    node.is_candidate = True

    # Earlier arrival check ensures this solution is better than the last one
    if node.walk_distance != -1:
      self.improved = True
      self.arrival = destination_arrival
      self.path_tail = PathSegment(node.stop_id, nb.int32(-1), nb.int32(node.walk_distance))


  def solve(self) -> Plan:
    while len(self.candidates) > 0:
      self.iteration += 1
      candidate = heapq.heappop(self.candidates)
      self.any_improved = False

      if candidate.destination_arrival >= self.arrival:
        break

      for stop_walk in self.stops.get_stop_walks(candidate.stop_id):
        node = self.get_node(stop_walk.stop_id)
        walk_time = int(stop_walk.distance / WALK_SPEED)
        walk_arrival = candidate.arrival + walk_time

        if walk_arrival < min(node.arrival, self.arrival):
          self.update_node(node, walk_arrival, candidate, -1, stop_walk.distance)

      for trip_id, stop_seq, departure in self.stops.get_stop_trips(candidate.stop_id):
        time = candidate.arrival - departure

        if candidate.trip_count > 0:
          time += TRANSFER_TIME

        start_time = self.trips.get_next_start(trip_id, self.services, time)

        if start_time == INF_TIME:
          continue

        if start_time + departure + candidate.estimate >= self.arrival:
          continue

        for to_stop, stop_arrival, _ in self.trips.get_stops_after(trip_id, stop_seq):
          node = self.get_node(to_stop)
          arrival = start_time + stop_arrival

          if arrival < min(node.arrival, self.arrival):
            self.update_node(node, arrival, candidate, trip_id, start_time + departure)
          elif arrival >= node.arrival + TRANSFER_TIME:
            break

      candidate.is_candidate = False
      self.add_candidates()

    return Plan(self.arrival, self.gather_path(self.path_tail))


  def add_candidates(self):
    if self.any_improved:
      if self.improved:
        self.improved = False
        old = self.candidates
        self.candidates = nb.typed.List.empty_list(_NB_NODE_TYPE)

        for c in old:
          if c.destination_arrival < self.arrival:
            self.candidates.append(c)
          else:
            c.is_candidate = False

        for c in self.new_candidates:
          if c.destination_arrival < self.arrival:
            self.candidates.append(c)
          else:
            c.is_candidate = False

      else:
        self.candidates.extend(self.new_candidates)

      heapq.heapify(self.candidates)
    else:
      for nc in self.new_candidates:
        heapq.heappush(self.candidates, nc)

    self.new_candidates.clear()


  def gather_path(self, segment):
    result = nb.typed.List.empty_list(_NB_PATH_SEGMENT_TYPE)

    while True:
      result.append(segment)

      if segment.from_stop == -1:
        result.reverse()
        return result
      else:
        segment = self.nodes[segment.from_stop].path_tail


  def stop_name(self, id):
    return self.stops[id].name


def get_stop_coords(max_stop_id: int, tdb: TransitDb) -> NDArray:
  res = tdb.sql("select unnest(coords) from stop order by id").arrow()
  return np.stack([res.field(0), res.field(1)], axis=-1)

def stop_ids(arr: pyarrow.StructArray) -> NDArray:
  return arr.field("id").to_numpy()

def stop_coords(arr: pyarrow.StructArray) -> NDArray:
  lat = arr.field("lat").to_numpy()
  lon = arr.field("lon").to_numpy()
  return np.stack([lat, lon], axis=-1)
