import asyncio
import cProfile
from dataclasses import dataclass
import datetime
import heapq
from itertools import chain
import math
import numba as nb # type: ignore
from numba.experimental import jitclass # type: ignore
import numba.types as nbt
import pyproj
import time as timer
from typing import NamedTuple, Optional, Union

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
  iterations: int


class NearStops(NamedTuple):
  position: Point
  ids: NDArray
  distances: NDArray

  @staticmethod
  def single(pos: Point, id: int):
    return NearStops(
      pos,
      np.array([id], dtype=np.int32),
      np.array([0.0], dtype=np.float32),
    )


class Router:
  tdb: TransitDb
  osrm: OsrmClient
  md: Metadata
  stops: Stops
  trips: Trips
  transformer: pyproj.Transformer

  def __init__(
    self,
    tdb: TransitDb,
    osrm: OsrmClient,
    md = None,
    stops = None,
    trips = None,
    transformer = None,
  ):
    self.tdb = tdb
    self.osrm = osrm
    self.md = md or tdb.get_metadata()
    self.stops = stops or tdb.get_stops()
    self.trips = trips or tdb.get_trips()
    self.transformer = transformer or pyproj.Transformer.from_proj('WGS84', self.md.projection)


  def clone(self):
    return Router(
      self.tdb.clone(),
      self.osrm,
      self.md,
      self.stops,
      self.trips,
      self.transformer,
    )


  async def find_route(
      self,
      start: Coords|int,
      destination: Coords|int,
      date_or_services: datetime.date|Services,
      time: datetime.time|int,
  ) -> Plan:
    if isinstance(time, int):
      start_time = time
    else:
      start_time = time.hour * 60*60 + time.minute * 60 + time.second

    if isinstance(date_or_services, Services):
      services = date_or_services
    else:
      services = self.tdb.get_services(date_or_services)

    walk_dst, near_start, near_destination = await self.get_walking_distances(start, destination)

    return find_route(
      self.stops,
      self.trips,
      near_start,
      near_destination,
      walk_dst,
      start_time,
      services,
    )


  def project(self, c: Coords) -> Point:
    x, y = self.transformer.transform(c.lat, c.lon)
    return Point(nb.float32(x - self.md.center.x), nb.float32(y - self.md.center.y))


  async def get_walking_distances(self, start, destination):
    if isinstance(start, Coords):
      start_coords = start
      near_start = None
    else:
      s = self.stops[start]
      start_coords = s.coords
      near_start = NearStops.single(s.position, start)

    if isinstance(destination, Coords):
      destination_coords = destination
      near_destination = None
    else:
      s = self.stops[destination]
      destination_coords = s.coords
      near_destination = NearStops.single(s.position, destination)

    walk_distance = None
    coroutines = []

    if near_start is None:
      pos = self.project(start_coords)
      ns_ids = self.tdb.nearest_stops(pos)

      async def get_near_start():
        nonlocal near_start, walk_distance

        distances = await self.osrm.distance_to_many(
          start_coords,
          chain((self.stops[id].coords for id in ns_ids), (destination_coords,)),
        )

        near_start = NearStops(pos, ns_ids, distances[:-1])
        walk_distance = distances[-1]

      coroutines.append(get_near_start())

    if near_destination is None:
      pos = self.project(destination_coords)
      nd_ids = self.tdb.nearest_stops(pos)

      async def get_near_destination(and_walk_distance: bool):
        nonlocal near_destination, walk_distance
        to_coords = [self.stops[id].coords for id in nd_ids]

        if and_walk_distance:
          to_coords.append(start_coords)

        distances = await self.osrm.distance_to_many(destination_coords, to_coords)
        near_destination = NearStops(pos, nd_ids, distances[:len(nd_ids)])

        if and_walk_distance:
          walk_distance = distances[-1]

      coroutines.append(get_near_destination(near_start is not None))

    if near_start is not None and near_destination is not None:
      async def get_walk_distance():
        nonlocal walk_distance
        distances = await self.osrm.distance_to_many(start_coords, [destination_coords])
        walk_distance = distances[0]

      coroutines.append(get_walk_distance())

    await asyncio.gather(*coroutines)
    return walk_distance, near_start, near_destination


_NB_POINT_TYPE = nbt.NamedUniTuple(nb.float32, 2, Point)
_NB_NEAR_STOPS_TYPE = nbt.NamedTuple([_NB_POINT_TYPE, nb.int32[::1], nb.float32[::1]], NearStops)
_NB_PATH_SEGMENT_TYPE = nbt.NamedUniTuple(nb.int32, 3, PathSegment)
_NB_PLAN_TYPE = nbt.NamedTuple([nb.int32, nbt.ListType(_NB_PATH_SEGMENT_TYPE), nb.int32], Plan)

@nb.jit
def empty_segment():
  return PathSegment(nb.int32(-1), nb.int32(-1), nb.int32(-1))


@jitclass([
  ("stop_id", nb.int32),
  ("estimate", nb.int32),
  ("walk_time", nb.int32),
  ("arrival", nb.int32),
  ("path_tail", _NB_PATH_SEGMENT_TYPE),
  ("is_candidate", nb.boolean),
])
class Node:
  def __init__(
    self,
    stop_id: int,
    estimate: int,
    walk_time: int,
  ):
    self.stop_id = stop_id
    self.estimate = estimate
    self.walk_time = walk_time
    self.arrival = INF_TIME
    self.path_tail = empty_segment()
    self.is_candidate = False

  def __lt__(self, other):
    return self.arrival + self.estimate < other.arrival + other.estimate


_NB_NODE_TYPE = Node.class_type.instance_type

@jitclass([
  ("stops", Stops.class_type.instance_type),
  ("trips", Trips.class_type.instance_type),
  ("services", Services.class_type.instance_type),
  ("near_destination", _NB_NEAR_STOPS_TYPE),

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
    stops: Stops,
    trips: Trips,
    near_start: NearStops,
    near_destination: NearStops,
    walk_distance: float,
    start_time: int,
    services: Services,
  ):
    self.stops = stops
    self.trips = trips
    self.services = services
    self.near_destination = near_destination

    self.improved = False
    self.arrival = start_time + int(walk_distance / WALK_SPEED)
    self.path_tail = PathSegment(nb.int32(-1), nb.int32(-1), nb.int32(walk_distance))

    self.nodes = nb.typed.Dict.empty(nb.int32, _NB_NODE_TYPE)
    self.candidates = nb.typed.List.empty_list(_NB_NODE_TYPE)
    self.any_improved = False
    self.new_candidates = nb.typed.List.empty_list(_NB_NODE_TYPE)
    self.arrival_to_beat = INF_TIME
    self.iteration = 0

    for id, dst in zip(near_destination.ids, near_destination.distances):
      walk_time = int(dst / WALK_SPEED)
      self.nodes[id] = Node(id, walk_time, walk_time)

    for id, dst in zip(near_start.ids, near_start.distances):
      n = self.get_node(id)
      n.arrival = start_time + int(dst / WALK_SPEED)
      n.path_tail = PathSegment(nb.int32(-1), nb.int32(-1), nb.int32(dst))
      n.is_candidate = True
      self.candidates.append(n)

    heapq.heapify(self.candidates)


  def get_node(self, stop_id: int) -> Node:
    node = self.nodes.get(stop_id, None)

    if node is None:
      node = Node(stop_id, self.estimate(stop_id), self.estimate_walk_time(stop_id))
      self.nodes[stop_id] = node

    return node


  def estimate(self, stop_id: int) -> int:
    pos = self.stops[stop_id].position
    result = INF_TIME

    for target_id, target_walk in zip(self.near_destination.ids, self.near_destination.distances):
      target_pos = self.stops[target_id].position
      distance = math.sqrt((pos.x - target_pos.x)**2 + (pos.y - target_pos.y)**2)
      result = min(result, int(distance / TRAM_SPEED + target_walk / WALK_SPEED))

    return result


  def estimate_walk_time(self, stop_id) -> int:
    a = self.stops[stop_id].position
    b = self.near_destination.position
    t = np.sqrt((a.x - b.x)**2 + (a.y - b.y)**2) * WALK_DISTANCE_MULTIPLIER / WALK_SPEED
    return nb.int32(t)


  def update_node(self, node: Node, arrival: int, came_from: Node, trip_id: int, details: int):
    if arrival + node.estimate >= self.arrival:
      return

    node.arrival = arrival
    node.path_tail = PathSegment(came_from.stop_id, nb.int32(trip_id), nb.int32(details))

    if node.is_candidate:
      self.any_improved = True
    else:
      self.new_candidates.append(node)

    node.is_candidate = True

    if arrival + node.walk_time < self.arrival:
      self.improved = True
      self.arrival = arrival + node.walk_time
      self.path_tail = PathSegment(node.stop_id, nb.int32(-1), nb.int32(node.walk_time*WALK_SPEED))


  def solve(self) -> Plan:
    while len(self.candidates) > 0:
      self.iteration += 1
      candidate = heapq.heappop(self.candidates)
      self.any_improved = False

      if candidate.arrival + candidate.estimate >= self.arrival:
        break

      for stop_walk in self.stops.get_stop_walks(candidate.stop_id):
        node = self.get_node(stop_walk.stop_id)
        walk_time = int(stop_walk.distance / WALK_SPEED)
        walk_arrival = candidate.arrival + walk_time

        if walk_arrival < min(node.arrival, self.arrival):
          self.update_node(node, walk_arrival, candidate, -1, stop_walk.distance)

      for trip_id, stop_seq, departure in self.stops.get_stop_trips(candidate.stop_id):
        time = candidate.arrival - departure

        if candidate.path_tail.from_stop != -1:
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

    return Plan(self.arrival, self.gather_path(self.path_tail), self.iteration)


  def add_candidates(self):
    if self.any_improved:
      if self.improved:
        self.improved = False
        old = self.candidates
        self.candidates = nb.typed.List.empty_list(_NB_NODE_TYPE)

        for c in old:
          if c.arrival + c.estimate < self.arrival:
            self.candidates.append(c)
          else:
            c.is_candidate = False

        for c in self.new_candidates:
          if c.arrival + c.estimate < self.arrival:
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


@nb.jit(
  _NB_PLAN_TYPE
  (
    Stops.class_type.instance_type,
    Trips.class_type.instance_type,
    _NB_NEAR_STOPS_TYPE,
    _NB_NEAR_STOPS_TYPE,
    nb.float32,
    nb.int64,
    Services.class_type.instance_type,
  ),
  nogil = True,
)
def find_route(
  stops: Stops,
  trips: Trips,
  near_start: NearStops,
  near_destination: NearStops,
  walk_distance: float,
  start_time: int,
  services: Services,
):
  return RouterTask(
    stops,
    trips,
    near_start,
    near_destination,
    walk_distance,
    start_time,
    services,
  ).solve()
