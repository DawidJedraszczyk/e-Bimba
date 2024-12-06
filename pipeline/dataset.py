#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor
import datetime
from enum import Enum
import numba as nb
import numba.np.numpy_support as nbp
import numba.types as nbt
import numpy as np
import os
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import pyproj
import random
import sys
import threading
from typing import NamedTuple

sys.path.append(str(Path(__file__).parents[1] / "ebus"))
sys.path.append(str(Path(__file__).parent))

from common import *

if len(sys.argv) == 1:
  print(f"Usage: {sys.argv[0]} CITY")
  sys.exit()
else:
  city_name = " ".join(sys.argv[1:])
  city = get_city(city_name)

  if city is None:
    print(f"Unknown city '{city_name}'")
    sys.exit()

from algorithm.estimators.cluster import cluster_estimator
from transit.data.misc import *
from transit.transitdb import *
from transit.osrm import *
from transit.prospector import *
from transit.router import *


class Destinations(Enum):
  RANDOM = 1
  GRID = 2
  STOP = 3


BATCH_SIZE = 1000
NUM_BATCHES = 128
TYPE = Destinations.GRID

FIELDS = [
  ("from_x", np.float32),
  ("from_y", np.float32),
  ("to_x", np.float32),
  ("to_y", np.float32),
  ("day_type", np.int8),
  ("start", np.float32),
  ("reference", np.int32),
  ("time", np.int32),
]


thread_local = threading.local()
tdb = TransitDb(DATA_CITIES / f"{city['id']}.db")
clustertimes = np.load(DATA_CITIES / f"{city['id']}-clustertimes.npy")
reference = cluster_estimator(clustertimes).estimate
prospector = Prospector(tdb, None)
stops = prospector.stops
router = Router(tdb, stops=stops)
trips = router.trips
stop_count = stops.count()


md = prospector.md
transformer = pyproj.Transformer.from_proj(md.projection, 'WGS84')
x_dev = np.std(stops.xs)
y_dev = np.std(stops.ys)


@jitclass([
  ("i", nb.int32),
  *((name, nbp.from_dtype(dtype)[:]) for name, dtype in FIELDS),
])
class Batch:
  def __init__(self):
    self.i = 0
    self.from_x = np.empty(BATCH_SIZE, np.float32)
    self.from_y = np.empty(BATCH_SIZE, np.float32)
    self.to_x = np.empty(BATCH_SIZE, np.float32)
    self.to_y = np.empty(BATCH_SIZE, np.float32)
    self.day_type = np.empty(BATCH_SIZE, np.int8)
    self.start = np.empty(BATCH_SIZE, np.float32)
    self.reference = np.empty(BATCH_SIZE, np.int32)
    self.time = np.empty(BATCH_SIZE, np.int32)

  def push(
    self,
    from_x,
    from_y,
    to_x,
    to_y,
    day_type,
    start,
    reference,
    time,
  ):
    if self.i == BATCH_SIZE:
      return

    self.from_x[self.i] = from_x / x_dev
    self.from_y[self.i] = from_y / y_dev
    self.to_x[self.i] = to_x / x_dev
    self.to_y[self.i] = to_y / y_dev
    self.day_type[self.i] = day_type
    self.start[self.i] = start / (24*60*60)
    self.reference[self.i] = reference
    self.time[self.i] = time
    self.i += 1


def batch_to_chunk(batch):
  return pa.StructArray.from_arrays(
    [getattr(batch, name) for name, _ in FIELDS],
    [name for name, _ in FIELDS]
  )


@nb.jit
def random_pos():
  return Point(
    np.float32(np.random.normal(0.0, x_dev/2)),
    np.float32(np.random.normal(0.0, y_dev/2)),
  )

def pos2coords(pos):
  lat, lon = transformer.transform(pos.x + md.center_position.x, pos.y + md.center_position.y)
  return Coords(lat, lon)

def random_stop():
  return random.randrange(0, stop_count)


s4dt = tdb.script("get-services-for-day-types").np()["services"]
workday_services = Services(today=s4dt[0], yesterday=s4dt[0], tomorrow=s4dt[0])
saturday_services = Services(today=s4dt[1], yesterday=s4dt[0], tomorrow=s4dt[2])
sunday_services = Services(today=s4dt[2], yesterday=s4dt[1], tomorrow=s4dt[0])
dt_services = [workday_services, saturday_services, sunday_services]

def random_day_type():
  return random.randrange(0, len(dt_services))

@nb.jit
def random_time():
  return random.randrange(0, 24*60*60)


@nb.jit(nogil=True)
def process(stops, trips, prospect, from_stop, day_type, services, batch):
  start = random_time()

  task = RouterTask(
    stops,
    trips,
    clustertimes,
    prospect,
    start,
    services,
  )

  plan = task.solve()

  batch.push(
    prospect.start.x,
    prospect.start.y,
    prospect.destination.x,
    prospect.destination.y,
    day_type,
    start,
    reference(stops, prospect, from_stop, None),
    plan.arrival - start,
  )

  if len(plan.path) > 3:
    stop_id = plan.path[random.randrange(3, len(plan.path))].from_stop
    node = task.nodes[stop_id]
    to_stop = stops[stop_id]

    prospect.destination = to_stop.position
    prospect.near_destination = [
      NearStop(sw.stop_id, nb.float32(sw.distance))
      for sw in stops.get_stop_walks(stop_id)
    ]

    batch.push(
      prospect.start.x,
      prospect.start.y,
      prospect.destination.x,
      prospect.destination.y,
      day_type,
      start,
      reference(stops, prospect, from_stop, None),
      node.arrival - start,
    )


def make_batch():
  local_prospector = getattr(thread_local, "prospector", None)

  if local_prospector is None:
    local_prospector = prospector.clone()
    thread_local.prospector = local_prospector

  batch = Batch()

  while batch.i < BATCH_SIZE:
    from_stop = random_stop()
    to_pos = random_pos()
    day_type = random_day_type()

    match TYPE:
      case Destinations.RANDOM:
        destination = random_pos()

      case Destinations.GRID:
        destination = osrm.nearest(pos2coords(random_pos()))

      case Destinations.STOP:
        destination = random_stop()

    prospect = local_prospector.prospect(from_stop, destination)
    process(stops, trips, prospect, from_stop, day_type, dt_services[day_type], batch)

  return batch_to_chunk(batch)


tp = ThreadPoolExecutor(max_workers=os.cpu_count())

with start_osrm(city["region"], instances=2) as osrm:
  prospector.osrm = osrm
  batches = list(tp.map(lambda _: make_batch(), range(NUM_BATCHES)))

table = pa.Table.from_struct_array(pa.chunked_array(batches))

now = datetime.datetime.now().isoformat()
out_path = TMP_CITIES / city['id'] / "dataset" / f"{now}.parquet"
out_path.parent.mkdir(parents=True, exist_ok=True)
pq.write_table(table, out_path)
