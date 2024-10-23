import asyncio
import cProfile
from dataclasses import dataclass
import datetime
from haversine import haversine, Unit # type: ignore
import heapq
from itertools import chain
import pyarrow
import time as timer
from typing import Optional

from lib.osrm import *
from lib.transitdb import *


WALK_SPEED = 1.25
TRAM_SPEED = 15

MAX_STOP_WALK = 1000
MAX_DESTINATION_WALK = 2000

TRANSFER_TIME = 3*60

INT32_MAX = 2**32-1
DAY = 24*60*60


@dataclass
class WalkFromBeg:
  distance: int

@dataclass
class WalkFromStop:
  stop_id: int
  distance: int

@dataclass
class TakeTrip:
  stop_id: int
  trip_id: int
  departure: int

PathSegment = WalkFromBeg | WalkFromStop | TakeTrip


@dataclass
class Node:
  stop_id: int
  estimate: int
  arrival: Optional[int] = None
  destination_arrival: Optional[int] = None
  came_from: Optional[PathSegment] = None
  is_candidate: bool = False

  def __lt__(self, other):
    return self.destination_arrival < other.destination_arrival

@dataclass
class TargetNode(Node):
  walk_distance: int = INT32_MAX


@dataclass
class Departures:
  departures: NDArray
  arrivals: NDArray
  trip_ids: NDArray

  @staticmethod
  def empty():
    a = np.array([], dtype=int)
    return Departures(a, a, a)

@dataclass
class Connection:
  to_stop: int
  walk_distance: int
  walk_time: int
  first_arrival_tomorrow: int
  last_departure_yesterday: int
  services: list[Departures]


class Router:
  tdb: TransitDb
  osrm: OsrmClient
  debug: bool
  max_service_id: int
  max_stop_id: int
  stop_coords: NDArray
  connections: list[list[Connection]]

  def __init__(self, tdb: TransitDb, osrm: OsrmClient, debug: bool = False):
    self.tdb = tdb
    self.osrm = osrm
    self.debug = debug
    self.max_service_id = tdb.sql("select max(id) from service").scalar()
    self.max_stop_id = tdb.sql("select max(id) from stop").scalar()
    self.stop_coords = get_stop_coords(self.max_stop_id, tdb)
    self.connections = get_connections(self.max_stop_id, self.max_service_id, tdb)

  async def find_route(
      self,
      from_lat: float,
      from_lon: float,
      to_lat: float,
      to_lon: float,
      date: datetime.date,
      time: datetime.time,
  ):
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

    RouterTask(
      to_lat, to_lon, self, walk_distance,
      Stops(stop_ids(from_stops), stop_coords(from_stops), walks_from[:-1]),
      Stops(stop_ids(to_stops), stop_coords(to_stops), walks_to),
      services, start_time,
    ).solve()


@dataclass
class Stops:
  ids: NDArray
  coords: NDArray
  distances: NDArray


class RouterTask:
  lat: float
  lon: float
  router: Router
  debug: bool

  srv_today: list[int]
  srv_yesterday: list[int]
  srv_tomorrow: list[int]
  to_stops: Stops

  arrival: int = INT32_MAX
  came_from: Optional[PathSegment] = None
  improved: bool = False

  nodes: list[Optional[Node]]
  candidates: list[Node] = []

  candidate_improved: bool = False
  new_candidates: list[Node] = []
  arrival_to_beat: int = INT32_MAX
  iteration: int = 0


  def __init__(
    self,
    lat: float,
    lon: float,
    router: Router,
    walk_distance: float,
    from_stops: Stops,
    to_stops: Stops,
    services: Services,
    start_time: int,
  ):
    self.lat = lat
    self.lon = lon
    self.router = router
    self.debug = router.debug
    self.srv_today = services["today"]
    self.srv_yesterday = services["yesterday"]
    self.srv_tomorrow = services["tomorrow"]
    self.to_stops = to_stops
    self.nodes = [None] * (router.max_stop_id + 1)
    self.candidates = []

    for id, dst in zip(to_stops.ids, to_stops.distances):
      self.nodes[id] = TargetNode(id, int(dst / WALK_SPEED), walk_distance=int(dst))

    for id, dst in zip(from_stops.ids, from_stops.distances):
      n = self.get_node(id)
      arrival = start_time + int(dst / WALK_SPEED)
      n.arrival = arrival
      n.destination_arrival = arrival + n.estimate
      n.came_from = WalkFromBeg(int(dst))
      n.is_candidate = True
      self.candidates.append(n)

    if walk_distance <= MAX_DESTINATION_WALK:
      self.arrival = start_time + int(walk_distance / WALK_SPEED)
      self.came_from = WalkFromBeg(int(walk_distance))

    heapq.heapify(self.candidates)


  def estimate(self, stop_id: int) -> int:
    coords = self.router.stop_coords[stop_id]
    result = INT32_MAX

    for target_coords, target_walk in zip(self.to_stops.coords, self.to_stops.distances):
      distance = haversine(coords, target_coords, Unit.METERS)
      result = min(result, int(distance / TRAM_SPEED + target_walk / WALK_SPEED))

    return result


  def get_node(self, stop_id: int) -> Node:
    node = self.nodes[stop_id]

    if node is None:
      node = Node(stop_id, self.estimate(stop_id))
      self.nodes[stop_id] = node

    return node


  def update_node(self, node: Node, came_from: PathSegment):
    arrival = self.arrival_to_beat
    destination_arrival = arrival + node.estimate

    if destination_arrival >= self.arrival:
      return

    node.arrival = arrival
    node.came_from = came_from
    node.destination_arrival = destination_arrival

    if node.is_candidate:
      self.candidate_improved = True
      if self.debug:
        print(f"    Improved candidate {node}")
    else:
      self.new_candidates.append(node)
      if self.debug:
        print(f"    New candidate {node}")

    node.is_candidate = True

    # Earlier arrival check ensures this solution is better than the last one
    if isinstance(node, TargetNode):
      if self.debug:
        print(f"      Solution improved by {arrival - destination_arrival} seconds")

      self.improved = True
      self.arrival = destination_arrival
      self.came_from = WalkFromStop(node.stop_id, node.walk_distance)


  def solve(self):
    while len(self.candidates) > 0:
      self.iteration += 1
      candidate = heapq.heappop(self.candidates)
      self.candidate_improved = False

      if candidate.destination_arrival >= self.arrival: # type: ignore
        break

      if self.debug:
        print(f"  Considering candidate {candidate} [{len(self.candidates)} other]")

      for conn in self.router.connections[candidate.stop_id]:
        node = self.get_node(conn.to_stop)

        if node.arrival is None or node.arrival > self.arrival:
          self.arrival_to_beat = self.arrival
        else:
          self.arrival_to_beat = node.arrival

        if candidate.arrival + conn.walk_time < self.arrival_to_beat:
          self.arrival_to_beat = candidate.arrival + conn.walk_time
          self.update_node(node, WalkFromStop(candidate.stop_id, conn.walk_distance))

        self.find_departure(node, candidate, conn, 0, self.srv_today)

        if self.arrival_to_beat > conn.first_arrival_tomorrow:
          self.find_departure(node, candidate, conn, DAY, self.srv_tomorrow)

        if candidate.arrival < conn.last_departure_yesterday:
          self.find_departure(node, candidate, conn, -DAY, self.srv_yesterday)

      candidate.is_candidate = False
      self.add_candidates()

    print(f"{self.arrival=} {self.came_from=} {self.iteration=}")

    if self.came_from is not None:
      self.print_path(self.came_from)


  def find_departure(self, node, candidate, conn, time_offset, services):
    for srv in services:
      service = conn.services[srv]
      departures = service.departures
      count = len(departures)

      if count == 0:
        continue

      i = departures.searchsorted(candidate.arrival + TRANSFER_TIME - time_offset)

      if i == count:
        continue

      arrival = service.arrivals[i] + time_offset

      if arrival < self.arrival_to_beat:
        self.arrival_to_beat = arrival
        path = TakeTrip(candidate.stop_id, service.trip_ids[i], departures[i] + time_offset)
        self.update_node(node, path)


  def add_candidates(self):
    if self.candidate_improved:
      if self.improved:
        self.improved = False
        old = self.candidates
        self.candidates = []

        for c in chain(old, self.new_candidates):
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


  def print_path(self, came_from: PathSegment):
    while True:
      print(came_from)
      match came_from:
        case WalkFromBeg(_):
          return
        case WalkFromStop(s, _):
          came_from = self.nodes[s].came_from # type: ignore
        case TakeTrip(s, _, _):
          came_from = self.nodes[s].came_from # type: ignore


def get_stop_coords(max_stop_id: int, tdb: TransitDb) -> NDArray:
  res = tdb.sql("select lat, lon from stop order by id").arrow()
  return np.stack([res.field(0), res.field(1)], axis=-1)


def get_connections(
  max_stop_id: int,
  max_service_id: int,
  tdb: TransitDb,
) -> list[list[Connection]]:
  empty_services = [Departures.empty()] * (max_service_id+1)
  result: list[list[Connection]] = [[]] * (max_stop_id+1)

  for connection in tdb.get_connections():
    from_stop = connection[0].as_py() # type: ignore
    to_stops = []

    for ts in connection[1].values: # type: ignore
      walk_distance = ts[1].as_py()

      if walk_distance is not None and walk_distance <= MAX_STOP_WALK:
        walk_time = int(walk_distance / WALK_SPEED)
      else:
        walk_time = INT32_MAX

      srv = ts[2].values
      first_arr_tomorrow = INT32_MAX
      last_dep_yesterday = 0

      if len(srv) > 0:
        services = empty_services.copy()
      else:
        services = empty_services

      for s in srv:
        deps = s[1].values

        if len(deps) == 0:
          continue

        service_id = s[0].as_py()
        departures = deps.field(0).to_numpy()
        arrivals = deps.field(1).to_numpy()

        first_arr_tomorrow = min(first_arr_tomorrow, arrivals[0] + DAY)
        last_dep_yesterday = max(last_dep_yesterday, departures[-1] - DAY)

        services[service_id] = Departures(
          departures,
          arrivals,
          deps.field(2).to_numpy(),
        )

      to_stops.append(
        Connection(
          ts[0].as_py(),
          walk_distance,
          walk_time,
          first_arr_tomorrow,
          last_dep_yesterday,
          services,
        )
      )

    result[from_stop] = to_stops

  return result


def stop_ids(arr: pyarrow.StructArray) -> NDArray:
  return arr.field("id").to_numpy()

def stop_coords(arr: pyarrow.StructArray) -> NDArray:
  lat = arr.field("lat").to_numpy()
  lon = arr.field("lon").to_numpy()
  return np.stack([lat, lon], axis=-1)
