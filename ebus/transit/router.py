import datetime
import math
import numba as nb
from numba.experimental import jitclass
import numba.types as nbt
import numpy as np
from typing import NamedTuple

from .data.misc import *
from .data.stops import Stops
from .data.trips import Trips
from .heapq import *
from .params import *
from .prospector import NearStop, Prospect
from .transitdb import *


class PathSegment(NamedTuple):
  from_stop: int
  trip_id: int
  details: int # departure if trip_id != -1, walk distance otherwise


class Plan(NamedTuple):
  arrival: int
  path: list[PathSegment]
  iterations: int


class Router:
  tdb: TransitDb
  clustertimes: np.ndarray
  stops: Stops
  trips: Trips

  def __init__(
    self,
    tdb: TransitDb,
    clustertimes = None,
    stops = None,
    trips = None,
  ):
    self.tdb = tdb
    self.clustertimes = clustertimes if clustertimes is not None else np.empty((0, 0), np.int32)
    self.stops = stops or tdb.get_stops()
    self.trips = trips or tdb.get_trips()


  def clone(self):
    return Router(
      self.tdb.clone(),
      self.clustertimes,
      self.stops,
      self.trips,
    )


  def find_route(
      self,
      prospect: Prospect,
      date_or_services: datetime.date|Services|None,
      time: datetime.time|int|None,
  ) -> Plan:
    if date_or_services is None or time is None:
      timeless = True
      start_time = 0
      services = Services.empty()
    else:
      timeless = False

      if isinstance(time, int):
        start_time = time
      else:
        start_time = time.hour * 60*60 + time.minute * 60 + time.second

      if isinstance(date_or_services, Services):
        services = date_or_services
      else:
        services = self.tdb.get_services(date_or_services)

    task = RouterTask(
      self.stops,
      self.trips,
      self.clustertimes,
      prospect.destination,
      prospect.walk_distance,
      prospect.near_start,
      prospect.near_destination,
      start_time,
      services,
    )

    if timeless:
      return solve_timeless(task)
    else:
      return solve(task)


def nbt_jitc(cls):
  if nb.config.DISABLE_JIT:
    return None
  else:
    return cls.class_type.instance_type

NbtPoint = nbt.NamedUniTuple(nb.float32, 2, Point)
NbtPathSegment = nbt.NamedUniTuple(nb.int32, 3, PathSegment)
NbtPlan = nbt.NamedTuple([nb.int32, nbt.ListType(NbtPathSegment), nb.int32], Plan)
NbtNearStop = nbt.NamedTuple([nb.int32, nb.float32], NearStop)

@nb.jit
def empty_segment():
  return PathSegment(nb.int32(-1), nb.int32(-1), nb.int32(-1))


@jitclass([
  ("arrival", nb.int32),
  ("estimate", nb.int32),
  ("heap_pos", nb.int32),
  ("stop_id", nb.int32),
  ("walk_time", nb.int32),
  ("path_tail", NbtPathSegment),
])
class Node:
  def __init__(
    self,
    stop_id: int,
    estimate: int,
    walk_time: int,
  ):
    self.arrival = INF_TIME
    self.estimate = estimate
    self.heap_pos = -1
    self.stop_id = stop_id
    self.walk_time = walk_time
    self.path_tail = empty_segment()

  def __lt__(self, other):
    return self.arrival + self.estimate < other.arrival + other.estimate

NbtNode = nbt_jitc(Node)


@jitclass([
  ("stops", nbt_jitc(Stops)),
  ("trips", nbt_jitc(Trips)),
  ("services", nbt_jitc(Services)),
  ("clustertimes", nb.int32[:, :]),

  ("destination", NbtPoint),
  ("near_destination", nbt.List(NbtNearStop)),

  ("iteration", nb.int32),
  ("arrival", nb.int32),
  ("path_tail", NbtPathSegment),
  ("exhaustive", nb.bool_),

  ("nodes", nbt.List(NbtNode)),
  ("queue", nbt.ListType(NbtNode)),
])
class RouterTask:
  def __init__(
    self,
    stops: Stops,
    trips: Trips,
    clustertimes: np.ndarray,
    destination: Point,
    walk_distance: float,
    near_start: list[NearStop],
    near_destination: list[NearStop],
    start_time: int,
    services: Services,
  ):
    self.stops = stops
    self.trips = trips
    self.clustertimes = clustertimes
    self.services = services
    self.destination = destination
    self.near_destination = [n for n in near_destination]

    self.iteration = 0
    self.arrival = start_time + int(walk_distance / WALK_SPEED)
    self.path_tail = PathSegment(nb.int32(-1), nb.int32(-1), nb.int32(walk_distance))
    self.exhaustive = False

    self.nodes = [Node(nb.int32(-1), nb.int32(-1), nb.int32(-1))] * stops.count()
    self.queue = nb.typed.List.empty_list(NbtNode)

    for id, dst in near_start:
      n = self.get_node(id)
      n.arrival = start_time + int(dst / WALK_SPEED)
      n.path_tail = PathSegment(nb.int32(-1), nb.int32(-1), nb.int32(dst))
      self.queue.append(n)

    heapify(self.queue)


  def get_node(self, stop_id: int) -> Node:
    node = self.nodes[stop_id]

    if node.stop_id == -1:
      walk_time = self.estimate_walk_time(stop_id)
      node = Node(stop_id, self.estimate(stop_id, walk_time), walk_time)
      self.nodes[stop_id] = node

    return node


  def estimate(self, stop_id: int, walk_time: int) -> int:
    pos = self.stops[stop_id].position
    result = walk_time

    if len(self.clustertimes) == 0:
      for near in self.near_destination:
        near_pos = self.stops[near.id].position
        distance = math.sqrt((pos.x - near_pos.x)**2 + (pos.y - near_pos.y)**2)
        time = nb.int32(distance / TRAM_SPEED + near.walk_distance / WALK_SPEED)
        result = min(result, time)
    else:
      from_cluster = self.stops[stop_id].cluster

      for near in self.near_destination:
        to_cluster = self.stops[near.id].cluster
        result = min(result, self.clustertimes[from_cluster, to_cluster])

    return result


  def estimate_walk_time(self, stop_id) -> int:
    for near in self.near_destination:
      if near.id == stop_id:
        return nb.int32(near.walk_distance / WALK_SPEED)

    a = self.stops[stop_id].position
    b = self.destination
    t = np.sqrt((a.x - b.x)**2 + (a.y - b.y)**2) * WALK_DISTANCE_MULTIPLIER / WALK_SPEED
    return nb.int32(t)


  def update_node(self, node: Node, arrival: int, came_from: Node, trip_id: int, details: int):
    if arrival + node.estimate >= self.arrival:
      return

    node.arrival = arrival
    node.path_tail = PathSegment(came_from.stop_id, nb.int32(trip_id), nb.int32(details))

    if node.heap_pos == -1:
      heappush(self.queue, node)
    else:
      heapdec(self.queue, node)

    if arrival + node.walk_time < self.arrival and not self.exhaustive:
      self.arrival = arrival + node.walk_time
      self.path_tail = PathSegment(node.stop_id, nb.int32(-1), nb.int32(node.walk_time*WALK_SPEED))


  def consider_walking(self, from_node: Node):
    for stop_walk in self.stops.get_stop_walks(from_node.stop_id):
      to_node = self.get_node(stop_walk.stop_id)
      arrival = from_node.arrival + int(stop_walk.distance / WALK_SPEED)

      if arrival < min(to_node.arrival, self.arrival):
        self.update_node(to_node, arrival, from_node, -1, stop_walk.distance)


  def solve(self) -> Plan:
    while self.queue:
      from_node = heappop(self.queue)

      if from_node.arrival + from_node.estimate >= self.arrival:
        break

      self.iteration += 1
      self.consider_walking(from_node)

      for trip_id, stop_seq, relative_departure in self.stops.get_stop_trips(from_node.stop_id):
        time = from_node.arrival - relative_departure

        if from_node.path_tail.from_stop != -1:
          time += TRANSFER_TIME

        start_time = self.trips.get_next_start(trip_id, self.services, time).time

        if start_time == INF_TIME:
          continue

        departure = start_time + relative_departure

        if departure + from_node.estimate >= self.arrival:
          continue

        for to_stop, relative_arrival, _ in self.trips.get_stops_after(trip_id, stop_seq):
          to_node = self.get_node(to_stop)
          arrival = start_time + relative_arrival

          if arrival < min(to_node.arrival, self.arrival):
            self.update_node(to_node, arrival, from_node, trip_id, departure)
          elif arrival >= to_node.arrival + TRANSFER_TIME:
            break

    return Plan(self.arrival, self.gather_path(self.path_tail), self.iteration)


  def solve_timeless(self) -> Plan:
    while self.queue:
      from_node = heappop(self.queue)

      if from_node.arrival + from_node.estimate >= self.arrival:
        break

      self.iteration += 1
      self.consider_walking(from_node)

      for trip_id, stop_seq, relative_departure in self.stops.get_stop_trips(from_node.stop_id):
        time = from_node.arrival - relative_departure

        if from_node.path_tail.from_stop != -1:
          time += TRANSFER_TIME

        for to_stop, relative_arrival, _ in self.trips.get_stops_after(trip_id, stop_seq):
          to_node = self.get_node(to_stop)
          arrival = time + relative_arrival

          if arrival < min(to_node.arrival, self.arrival):
            self.update_node(to_node, arrival, from_node, trip_id, time + relative_departure)
          elif arrival >= to_node.arrival + TRANSFER_TIME:
            break

    return Plan(self.arrival, self.gather_path(self.path_tail), self.iteration)


  def gather_path(self, segment):
    result = nb.typed.List.empty_list(NbtPathSegment)

    while True:
      result.append(segment)

      if segment.from_stop == -1:
        result.reverse()
        return result
      else:
        segment = self.nodes[segment.from_stop].path_tail


@nb.jit(nogil=True)
def solve(task):
  return task.solve()

@nb.jit(nogil=True)
def solve_timeless(task):
  return task.solve_timeless()
