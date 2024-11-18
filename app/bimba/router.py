import datetime
import math
import numba as nb
from numba.experimental import jitclass
import numba.types as nbt
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
  stops: Stops
  trips: Trips

  def __init__(
    self,
    tdb: TransitDb,
    stops = None,
    trips = None,
  ):
    self.tdb = tdb
    self.stops = stops or tdb.get_stops()
    self.trips = trips or tdb.get_trips()


  def clone(self):
    return Router(
      self.tdb.clone(),
      self.stops,
      self.trips,
    )


  def find_route(
      self,
      prospect: Prospect,
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

    return find_route(
      self.stops,
      self.trips,
      prospect,
      start_time,
      services,
    )


_NB_POINT_TYPE = nbt.NamedUniTuple(nb.float32, 2, Point)
_NB_PATH_SEGMENT_TYPE = nbt.NamedUniTuple(nb.int32, 3, PathSegment)
_NB_PLAN_TYPE = nbt.NamedTuple([nb.int32, nbt.ListType(_NB_PATH_SEGMENT_TYPE), nb.int32], Plan)
_NB_NEAR_DESTINATION_TUPLE_TYPE = nbt.UniTuple(nb.int32, 2)
_NB_NEAR_STOP_TYPE = nbt.NamedTuple([nb.int32, nb.float32], NearStop)

_NB_PROSPECT_TYPE = nbt.NamedTuple(
  [
    _NB_POINT_TYPE,
    _NB_POINT_TYPE,
    nb.float32,
    nbt.List(_NB_NEAR_STOP_TYPE, reflected=True),
    nbt.List(_NB_NEAR_STOP_TYPE, reflected=True),
  ],
  Prospect,
)

@nb.jit
def empty_segment():
  return PathSegment(nb.int32(-1), nb.int32(-1), nb.int32(-1))


@jitclass([
  ("arrival", nb.int32),
  ("estimate", nb.int32),
  ("heap_pos", nb.int32),
  ("stop_id", nb.int32),
  ("walk_time", nb.int32),
  ("path_tail", _NB_PATH_SEGMENT_TYPE),
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

_NB_NODE_TYPE = Node.class_type.instance_type


@jitclass([
  ("stops", Stops.class_type.instance_type),
  ("trips", Trips.class_type.instance_type),
  ("services", Services.class_type.instance_type),

  ("destination", _NB_POINT_TYPE),
  ("near_destination", nbt.ListType(_NB_NEAR_DESTINATION_TUPLE_TYPE)),

  ("iteration", nb.int32),
  ("arrival", nb.int32),
  ("path_tail", _NB_PATH_SEGMENT_TYPE),

  ("nodes", nbt.DictType(nb.int32, _NB_NODE_TYPE)),
  ("queue", nbt.ListType(_NB_NODE_TYPE)),
])
class RouterTask:
  def __init__(
    self,
    stops: Stops,
    trips: Trips,
    prospect: Prospect,
    start_time: int,
    services: Services,
  ):
    self.stops = stops
    self.trips = trips
    self.services = services

    self.destination = prospect.destination
    self.near_destination = nb.typed.List.empty_list(_NB_NEAR_DESTINATION_TUPLE_TYPE)

    self.iteration = 0
    self.arrival = start_time + int(prospect.walk_distance / WALK_SPEED)
    self.path_tail = PathSegment(nb.int32(-1), nb.int32(-1), nb.int32(prospect.walk_distance))

    self.nodes = nb.typed.Dict.empty(nb.int32, _NB_NODE_TYPE)
    self.queue = nb.typed.List.empty_list(_NB_NODE_TYPE)

    all_near = [(ns.walk_distance, ns.id) for ns in prospect.near_destination]
    all_near.sort()

    for dst, id in all_near:
      walk_time = nb.int32(dst / WALK_SPEED)
      self.nodes[id] = Node(id, self.estimate(id, walk_time), walk_time)
      self.near_destination.append((walk_time, id))

    for id, dst in prospect.near_start:
      n = self.get_node(id)
      n.arrival = start_time + int(dst / WALK_SPEED)
      n.path_tail = PathSegment(nb.int32(-1), nb.int32(-1), nb.int32(dst))
      self.queue.append(n)

    heapify(self.queue)


  def get_node(self, stop_id: int) -> Node:
    node = self.nodes.get(stop_id, None)

    if node is None:
      walk_time = self.estimate_walk_time(stop_id)
      node = Node(stop_id, self.estimate(stop_id, walk_time), walk_time)
      self.nodes[stop_id] = node

    return node


  def estimate(self, stop_id: int, walk_time: int) -> int:
    pos = self.stops[stop_id].position
    result = walk_time

    for target_walk_time, target_id in self.near_destination:
      target_pos = self.stops[target_id].position
      distance = math.sqrt((pos.x - target_pos.x)**2 + (pos.y - target_pos.y)**2)
      time = nb.int32(int(distance / TRAM_SPEED) + target_walk_time)
      result = min(result, time)

    return result


  def estimate_walk_time(self, stop_id) -> int:
    a = self.stops[stop_id].position
    b = self.destination
    t = np.sqrt((a.x - b.x)**2 + (a.y - b.y)**2) * WALK_DISTANCE_MULTIPLIER / WALK_SPEED
    return nb.int32(t)


  def update_node(self, node: Node, arrival: int, came_from: Node, trip_id: int, details: int):
    if arrival + node.estimate >= self.arrival:
      return

    node.arrival = arrival
    node.path_tail = PathSegment(came_from.stop_id, nb.int32(trip_id), nb.int32(details))
    heappush(self.queue, node)

    if arrival + node.walk_time < self.arrival:
      self.arrival = arrival + node.walk_time
      self.path_tail = PathSegment(node.stop_id, nb.int32(-1), nb.int32(node.walk_time*WALK_SPEED))


  def solve(self) -> Plan:
    while len(self.queue) > 0:
      from_node = heappop(self.queue)

      if from_node.arrival + from_node.estimate >= self.arrival:
        break

      self.iteration += 1

      for stop_walk in self.stops.get_stop_walks(from_node.stop_id):
        to_node = self.get_node(stop_walk.stop_id)
        arrival = from_node.arrival + int(stop_walk.distance / WALK_SPEED)

        if arrival < min(to_node.arrival, self.arrival):
          self.update_node(to_node, arrival, from_node, -1, stop_walk.distance)

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
    _NB_PROSPECT_TYPE,
    nb.int64,
    Services.class_type.instance_type,
  ),
  nogil = True,
)
def find_route(
  stops: Stops,
  trips: Trips,
  prospect: Prospect,
  start_time: int,
  services: Services,
):
  return RouterTask(
    stops,
    trips,
    prospect,
    start_time,
    services,
  ).solve()
