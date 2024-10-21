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
  arrival: Optional[int] = None
  estimate: Optional[int] = None
  came_from: Optional[PathSegment] = None
  is_candidate: bool = False

  def __lt__(self, other):
    return self.estimate < other.estimate


@dataclass
class TargetNode(Node):
  walk_distance: int = INT32_MAX


@dataclass
class Connection:
  to_stop: int
  walk_distance: int
  walk_time: int
  first_tomorrow: int
  last_yesterday: int
  departures: NDArray
  arrivals: NDArray
  service_ids: NDArray
  trip_ids: NDArray


class Router:
  tdb: TransitDb
  osrm: OsrmClient
  debug: bool
  max_stop_id: int
  stop_coords: NDArray
  connections: list[list[Connection]]

  def __init__(self, tdb: TransitDb, osrm: OsrmClient, debug: bool = False):
    self.tdb = tdb
    self.osrm = osrm
    self.debug = debug
    self.max_stop_id = tdb.sql("select max(id) from stop").scalar()
    self.stop_coords = get_stop_coords(self.max_stop_id, tdb)
    self.connections = get_connections(self.max_stop_id, tdb)

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
      zip(stop_ids(from_stops), walks_from), zip(stop_ids(to_stops), walks_to),
      services, start_time,
    ).solve()

  def estimate(self, stop_id: int, lat: float, lon: float) -> int:
    s_lat, s_lon = self.stop_coords[stop_id]
    distance = haversine((s_lat, s_lon), (lat, lon), Unit.METERS)
    return int(distance / TRAM_SPEED)


class RouterTask:
  lat: float
  lon: float
  router: Router
  debug: bool

  srv_today: list[int]
  srv_yesterday: list[int]
  srv_tomorrow: list[int]

  arrival: int = INT32_MAX
  came_from: Optional[PathSegment] = None
  improved: bool = False

  nodes: list[Optional[Node]]
  candidates: list[Node] = []

  candidate_improved: bool = False
  new_candidates: list[Node] = []
  arrival_to_beat: int = INT32_MAX


  def __init__(
    self,
    lat: float,
    lon: float,
    router: Router,
    walk_distance: float,
    from_stops: Iterable[tuple[int, float]],
    to_stops: Iterable[tuple[int, float]],
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
    self.nodes = [None] * (router.max_stop_id + 1)
    self.candidates = []

    for id, dst in to_stops:
      self.nodes[id] = TargetNode(id, walk_distance=int(dst))

    for id, dst in from_stops:
      n = self.get_node(id)
      arrival = start_time + int(dst / WALK_SPEED)
      n.arrival = arrival
      n.estimate = arrival + router.estimate(id, lat, lon)
      n.came_from = WalkFromBeg(int(dst))
      n.is_candidate = True
      self.candidates.append(n)

    if walk_distance <= MAX_DESTINATION_WALK:
      self.arrival = start_time + int(walk_distance / WALK_SPEED)
      self.came_from = WalkFromBeg(int(walk_distance))

    heapq.heapify(self.candidates)


  def get_node(self, stop_id: int) -> Node:
    node = self.nodes[stop_id]

    if node is None:
      node = Node(stop_id)
      self.nodes[stop_id] = node

    return node


  def update_node(self, node: Node, came_from: PathSegment):
    arrival = self.arrival_to_beat
    estimate = arrival + self.router.estimate(node.stop_id, self.lat, self.lon)

    if estimate >= self.arrival:
      return

    node.arrival = arrival
    node.came_from = came_from
    node.estimate = estimate

    if node.is_candidate:
      self.candidate_improved = True
      if self.debug:
        print(f"    Improved candidate {node}")
    else:
      self.new_candidates.append(node)
      if self.debug:
        print(f"    New candidate {node}")

    node.is_candidate = True

    if isinstance(node, TargetNode):
      new_arrival = arrival + int(node.walk_distance / WALK_SPEED)

      if new_arrival < self.arrival:
        if self.debug:
          print(f"      Solution improved by {arrival - new_arrival} seconds")

        self.improved = True
        self.arrival = new_arrival
        self.came_from = WalkFromStop(node.stop_id, node.walk_distance)


  def solve(self):
    while len(self.candidates) > 0:
      candidate = heapq.heappop(self.candidates)
      self.candidate_improved = False

      if candidate.estimate >= self.arrival: # type: ignore
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

        if len(conn.departures) == 0:
          continue

        self.find_departure(node, candidate, conn, 0, self.srv_today)

        if self.arrival_to_beat > conn.first_tomorrow:
          self.find_departure(node, candidate, conn, DAY, self.srv_tomorrow)

        if self.arrival_to_beat < conn.last_yesterday:
          self.find_departure(node, candidate, conn, -DAY, self.srv_yesterday)

      candidate.is_candidate = False
      self.add_candidates()

    print(f"{self.arrival=} {self.came_from=}")

    if self.came_from is not None:
      self.print_path(self.came_from)


  def find_departure(self, node, candidate, conn, time_offset, services):
    departures = conn.departures
    start_index = departures.searchsorted(candidate.arrival + TRANSFER_TIME - time_offset)

    for i in range(start_index, len(departures)):
      if conn.service_ids[i] not in services:
        continue

      arrival = conn.arrivals[i] + time_offset

      if arrival < self.arrival_to_beat:
        self.arrival_to_beat = arrival
        self.update_node(node, TakeTrip(candidate.stop_id, conn.trip_ids[i], departures[i]))

      break


  def add_candidates(self):
    if self.candidate_improved:
      if self.improved:
        self.improved = False
        old = self.candidates
        self.candidates = []

        for c in chain(old, self.new_candidates):
          if c.estimate < self.arrival:
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
  res = [(0.0, 0.0)] * (max_stop_id + 1)

  for row in tdb.sql("select id, lat, lon from stop").arrow():
    res[row["id"].as_py()] = (row["lat"].as_py(), row["lon"].as_py())

  return np.array(res)


def get_connections(max_stop_id: int, tdb: TransitDb) -> list[list[Connection]]:
  result: list[list[Connection]] = [[]] * (max_stop_id+1)

  for connection in tdb.get_connections():
    from_stop = connection[0].as_py() # type: ignore
    to_stops = []

    for ts in connection[1].values: # type: ignore
      walk_distance = ts[1].as_py()

      if walk_distance > 0 and walk_distance <= MAX_STOP_WALK:
        walk_time = int(walk_distance / WALK_SPEED)
      else:
        walk_time = INT32_MAX

      deps = ts[2].values
      arrivals = deps.field(1).to_numpy()

      if len(arrivals) == 0:
        first_tomorrow = INT32_MAX
        last_yesterday = INT32_MAX
      else:
        first_tomorrow = arrivals[0] + DAY
        last_yesterday = arrivals[-1] - DAY

      to_stops.append(
        Connection(
          ts[0].as_py(),
          walk_distance,
          walk_time,
          first_tomorrow,
          last_yesterday,
          deps.field(0).to_numpy(),
          arrivals,
          deps.field(2).to_numpy(),
          deps.field(3).to_numpy(),
        )
      )

    result[from_stop] = to_stops
  
  return result


def stop_ids(arr: pyarrow.StructArray) -> Iterable[int]:
  for row in arr:
    yield row["id"].as_py()

def stop_coords(arr: pyarrow.StructArray) -> Iterable[tuple[float, float]]:
  for row in arr:
    yield row["lat"].as_py(), row["lon"].as_py()
