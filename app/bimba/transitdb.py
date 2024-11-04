import asyncio
from dataclasses import dataclass
import datetime
import duckdb
import functools
import numpy as np
import os
from pathlib import Path
import pyarrow
import time
from typing import TypedDict, cast

from bimba.connections import Connections, connections_from_arrow
from bimba.db import Db
from bimba.osrm import OsrmClient
import bimba.params as params


class Services(TypedDict):
  yesterday: list[int]
  today: list[int]
  tomorrow: list[int]


class TransitDb(Db):
  OPTIONAL_GTFS_FILES = [
    "calendar.txt",
    "calendar_dates.txt",
    "feed_info.txt",
    "frequencies.txt",
  ]

  def __init__(self, path: Path):
    scripts = Path(__file__).parent / "sql"
    variables = {k: v for k, v in params.__dict__.items() if not k.startswith('_')}
    super().__init__(path, scripts, variables)
    self.db.sql("install spatial; load spatial")


  def get_services(self, date: datetime.date) -> Services:
    return self.sql("select get_service_lists(?)", (date,)).scalar()

  def nearest_stops(self, lat: float, lon: float) -> pyarrow.StructArray:
    return self.script("get-nearest-stops", {"lat":lat, "lon":lon}).arrow()

  def get_connections(self) -> Connections:
    cs = self.sql("select to_stops from connections order by from_stop").arrow().field(0)
    return connections_from_arrow(cast(pyarrow.ListArray, cs))


  def init_schema(self):
    print("Initializing schema")
    self.script("init")


  def import_gtfs(self, gtfs_folder: Path):
    print(f"Importing GTFS from '{gtfs_folder}'")
    self.set_variable('GTFS_FOLDER', str(gtfs_folder))

    t0 = time.time()
    self.script("gtfs/init")
    self.script("gtfs/import/required")

    for opt_gtfs in self.OPTIONAL_GTFS_FILES:
      if (gtfs_folder / opt_gtfs).exists():
        self.script(f"gtfs/import/{opt_gtfs[:-4].replace("_", "-")}")

    t1 = time.time()
    self.script("gtfs/process/assign-id")
    self.script("gtfs/process/services")
    self.script("gtfs/process/shapes")
    self.script("gtfs/process/trips")

    t2 = time.time()
    self.script("gtfs/insert")
    self.script("gtfs/clean-up")

    t3 = time.time()
    print(f"Time: {_t(t2, t0)}"
      f"(parsing: {_t(t1, t0)}, processing: {_t(t2, t1)}, inserting: {_t(t3, t2)})")


  async def calculate_stop_walks(self, osrm: OsrmClient):
    t0 = time.time()
    print("Calculating walking distances between stops")
    inputs = self.script("init-stop-walk").arrow()
    sem = asyncio.Semaphore(os.cpu_count())

    async def task(row):
      async with sem:
        from_id = row["id"]
        from_lat = row["lat"]
        from_lon = row["lon"]
        to_stops = row["to_stops"].values
        to_ids = to_stops.field("id").to_numpy()
        to_lats = to_stops.field("lat").to_numpy()
        to_lons = to_stops.field("lon").to_numpy()

        distances = await osrm.distance_to_many(from_lat, from_lon, zip(to_lats, to_lons))
        return from_id, to_ids, distances

    for task in [asyncio.create_task(task(row)) for row in inputs]:
      from_id, to_ids, distances = await task
      from_ids = np.repeat(from_id, len(to_ids))

      self.sql(
        "insert into stop_walk from result",
        views = {
          "result": pyarrow.table(
            [from_ids, to_ids, distances],
            ["from_stop", "to_stop", "distance"],
          )
        },
      )
    
    t1 = time.time()
    print(f"Time: {_t(t1, t0)}")


  def finalize(self):
    t0 = time.time()
    print("Finalizing")
    self.script("finalize")

    t1 = time.time()
    print(f"Time: {_t(t1, t0)}")


def _t(t_to, t_from):
  return f"{round(t_to - t_from, 3)}s"
