#!/usr/bin/env python3

import asyncio
from concurrent.futures import ThreadPoolExecutor
import numba as nb
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
import time
from typing import NamedTuple

sys.path.append(str(Path(__file__).parents[1] / "app"))
sys.path.append(str(Path(__file__).parent))

from common import *

if len(sys.argv) == 1:
  print(f"Usage: {sys.argv[0]} CITY")
  sys.exit()
else:
  city_name = " ".join(sys.argv[1:])

  if city_name not in CITIES:
    print(f"Unknown city '{city_name}'")
    sys.exit()
  else:
    city = CITIES[city_name]

from apps.route_search.modules.algorithm_parts.utils import seconds_to_time
from bimba.data.misc import *
from bimba.transitdb import *
from bimba.osrm import *
from bimba.router import *


BATCH_SIZE = 1000
NUM_BATCHES = 12


class Row(NamedTuple):
  stop_lat: float
  stop_lon: float
  point_lat: float
  point_lon: float
  day_type: int
  start_time: int
  arrival: int


thread_local = threading.local()
tdb = TransitDb(DATA_CITIES / city["database"])
osrm = OsrmClient(f"http://localhost:{OSRM_PORT}")
router = Router(tdb, osrm)
stops = router.stops
stop_count = stops.count()
routes = tdb.get_routes()


md = router.md
transformer = pyproj.Transformer.from_proj(md.projection, 'WGS84')
x_d = np.std(stops.xs) / 2
y_d = np.std(stops.ys) / 2

@nb.jit
def random_pos():
  return Point(np.random.normal(0.0, x_d), np.random.normal(0.0, y_d))

def pos2coords(pos):
  lat, lon = transformer.transform(pos.x + md.center.x, pos.y + md.center.y)
  return Coords(lat, lon)

def random_coords():
  return pos2coords(random_pos())

def random_stop():
  return random.randrange(0, stop_count)


s4dt = tdb.script("get-services-for-day-types").np()["services"]
workday_services = Services(today=s4dt[0], yesterday=s4dt[0], tomorrow=s4dt[0])
saturday_services = Services(today=s4dt[1], yesterday=s4dt[0], tomorrow=s4dt[2])
sunday_services = Services(today=s4dt[2], yesterday=s4dt[1], tomorrow=s4dt[0])
dt_services = [workday_services, saturday_services, sunday_services]

def random_day_type():
  return random.randrange(0, len(dt_services))

def random_time():
  return random.randrange(0, 24*60*60)


def make_batch():
  local_router = getattr(thread_local, "router", None)

  if local_router is None:
    local_router = router.clone()
    thread_local.router = local_router

  rows = []

  for _ in range(BATCH_SIZE):
    from_stop = random_stop()
    to_coords = random_coords()
    day_type = random_day_type()
    start_time = random_time()

    plan = asyncio.run(
      local_router.find_route(from_stop, to_coords, dt_services[day_type], start_time)
    )

    rows.append(Row(
      np.float32(stops[from_stop].coords.lat),
      np.float32(stops[from_stop].coords.lon),
      np.float32(to_coords.lat),
      np.float32(to_coords.lon),
      np.int8(day_type),
      np.int32(start_time),
      np.int32(plan.arrival),
    ))

  return pa.StructArray.from_arrays(
    ([getattr(r, f) for r in rows] for f in Row._fields),
    Row._fields,
  )


tp = ThreadPoolExecutor(max_workers=os.cpu_count())

with start_osrm(city["region"]):
  batches = list(tp.map(lambda _: make_batch(), range(NUM_BATCHES)))

table = pa.Table.from_struct_array(pa.chunked_array(batches))
pq.write_table(table, TMP_CITIES / city["database"].replace(".db", "-dataset.parquet"))
