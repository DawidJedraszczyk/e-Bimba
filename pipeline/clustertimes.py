#!/usr/bin/env python3

import asyncio
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import numba as nb
from numba.experimental import jitclass
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

FDIR = Path(__file__).parent
sys.path.append(str(FDIR.parent / "ebus"))
sys.path.append(str(FDIR))

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

from transit.data.misc import *
from transit.transitdb import *
from transit.prospector import Prospect, NearStop
from transit.router import *


@jitclass([
  ("count", nb.int32),
  ("centers", nbt.List(NbtPoint)),
  ("stops", nbt.List(nbt.List(NbtNearStop))),
])
class Clusters:
  def __init__(self, xs, ys, stops):
    self.count = nb.int32(len(xs))
    self.centers = [Point(x, y) for x, y in zip(xs, ys)]
    self.stops = [[NearStop(s, nb.float32(0)) for s in sids] for sids in stops]


def get_clusters(tdb: TransitDb):
  ids, xs, ys, stops = tdb.sql("""
    select
      cluster as id,
      avg(position.x) :: float4 as x,
      avg(position.y) :: float4 as y,
      list(id) as stops,
    from stop
    group by cluster
    order by cluster
  """).arrow().flatten()

  assert np.array_equal(ids, np.arange(len(ids)))
  return Clusters(xs.to_numpy(), ys.to_numpy(), list(stops.to_numpy(False)))


@nb.jit
def distance(a, b) -> np.float32:
  return np.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

@nb.jit
def distance_m(a, b) -> np.float32:
  return np.abs(a.x - b.x) + np.abs(a.y - b.y)


@nb.jit(nogil=True)
def calculate_times(from_cluster, clusters, stops, trips, empty_services):
  result = np.empty(clusters.count, dtype=np.int32)

  prospect = Prospect(
    clusters.centers[from_cluster],
    Coords(np.float32(0), np.float32(0)),
    clusters.stops[from_cluster],
    clusters.centers[from_cluster],
    Coords(np.float32(0), np.float32(0)),
    clusters.stops[from_cluster],
    np.float32(0),
  )

  task = RouterTask(
    stops,
    trips,
    np.empty((0, 0), np.int32),
    prospect,
    0,
    empty_services,
  )

  task.arrival = INF_TIME
  task.exhaustive = True
  task.solve_timeless()

  for to_cluster in range(clusters.count):
    if to_cluster == from_cluster:
      result[to_cluster] = 0
      continue

    time = INF_TIME

    for stop in clusters.stops[to_cluster]:
      time = min(time, task.get_node(stop.id).arrival)

    result[to_cluster] = time

  return result


tp = ThreadPoolExecutor(max_workers=os.cpu_count())
tdb = TransitDb(DATA_CITIES / f"{city['id']}.db")
stops = tdb.get_stops()
trips = tdb.get_trips()
clusters = get_clusters(tdb)
empty_services = Services.empty()


def do_calc(i):
  return calculate_times(i, clusters, stops, trips, empty_services)

results = list(tp.map(do_calc, range(clusters.count)))
np.save(DATA_CITIES / f"{city['id']}-clustertimes.npy", np.array(results))
