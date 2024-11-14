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
import pyarrow
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
  ids: NDArray
  distances: NDArray

  @staticmethod
  def single(id: int):
    return NearStops(
      np.array([id], dtype=np.int32),
      np.array([0.0], dtype=np.float32),
    )


class Router:
  tdb: TransitDb
  osrm: OsrmClient
  stops: Stops
  trips: Trips

  def __init__(
    self,
    tdb: TransitDb,
    osrm: OsrmClient,
    stops = None,
    trips = None,
  ):
    self.tdb = tdb
    self.osrm = osrm
    self.stops = stops or tdb.get_stops()
    self.trips = trips or tdb.get_trips()

  def copy():
    return Router(
      self.tdb.cursor(),
      self.osrm,
      self.stops,
      self.trips,
    )

  def find_route(
      self,
      start: Coords|int,
      destination: Coords|int,
      date: datetime.date,
      time: datetime.time,
  ) -> Plan:
    start_time = time.hour * 60*60 + time.minute * 60 + time.second
    services = self.tdb.get_services(date)

    walk_distance, near_start, near_destination = asyncio.run(
      self.get_walking_distances(start, destination)
    )

    return find_route(
      self.stops,
      self.trips,
      near_start,
      near_destination,
      walk_distance,
      start_time,
      services,
    )


  async def get_walking_distances(self, start, destination):
    if isinstance(start, Coords):
      start_coords = start
      near_start = None
    else:
      start_coords = self.stops[start].coords
      near_start = NearStops.single(start)

    if isinstance(destination, Coords):
      destination_coords = destination
      near_destination = None
    else:
      destination_coords = self.stops[destination].coords
      near_destination = NearStops.single(destination)

    walk_distance = None
    coroutines = []

    if near_start is None:
      ns_ids = self.tdb.nearest_stops(start_coords)

      async def get_near_start():
        nonlocal near_start, walk_distance

        distances = await self.osrm.distance_to_many(
          start_coords,
          chain((self.stops[id].coords for id in ns_ids), (destination_coords,)),
        )

        near_start = NearStops(ns_ids, distances[:-1])
        walk_distance = distances[-1]

      coroutines.append(get_near_start())

    if near_destination is None:
      nd_ids = self.tdb.nearest_stops(destination_coords)

      async def get_near_destination(and_walk_distance: bool):
        nonlocal near_destination, walk_distance
        to_coords = [self.stops[id].coords for id in nd_ids]

        if and_walk_distance:
          to_coords.append(start_coords)

        distances = await self.osrm.distance_to_many(destination_coords, to_coords)
        near_destination = NearStops(nd_ids, distances[:len(nd_ids)])

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


_NB_NEAR_STOPS_TYPE = nbt.NamedTuple([nb.int32[::1], nb.float32[::1]], NearStops)
_NB_PATH_SEGMENT_TYPE = nbt.NamedUniTuple(nb.int32, 3, PathSegment)
_NB_PLAN_TYPE = nbt.NamedTuple([nb.int32, nbt.ListType(_NB_PATH_SEGMENT_TYPE), nb.int32], Plan)

@nb.jit
def empty_segment():
  return PathSegment(nb.int32(-1), nb.int32(-1), nb.int32(-1))


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


_NB_NODE_TYPE = Node.class_type.instance_type

@jitclass([
  ("stops", Stops.class_type.instance_type),
  ("trips", Trips.class_type.instance_type),
  ("services", Services.class_type.instance_type),
  ("to_stops", _NB_NEAR_STOPS_TYPE),

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
    self.to_stops = near_destination

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
      self.nodes[id] = Node(id, int(dst / WALK_SPEED), int(dst))

    for id, dst in zip(near_start.ids, near_start.distances):
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
    pos = self.stops[stop_id].position
    result = INF_TIME

    for target_id, target_walk in zip(self.to_stops.ids, self.to_stops.distances):
      target_pos = self.stops[target_id].position
      distance = math.sqrt((pos.x - target_pos.x)**2 + (pos.y - target_pos.y)**2)
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

    return Plan(self.arrival, self.gather_path(self.path_tail), self.iteration)


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
  cache = True,
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
