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
    self.script("gtfs/import")

    t1 = time.time()
    self.sql("begin transaction")
    self.script("gtfs/assign-tdb-id")
    self.script("gtfs/insert")
    self.sql("commit")
    self.script("gtfs/clean-up")

    t2 = time.time()
    print(f"Time: {_t(t2, t0)} (parsing: {_t(t1, t0)}, inserting: {_t(t2, t1)})")


  async def generate_connections(self, osrm: OsrmClient):
    t0 = time.time()
    await self._calc_stop_walks(osrm)

    t1 = time.time()
    print("Generating connections")
    self.script("generate-connections")

    t2 = time.time()
    self.sql("analyze")

    t3 = time.time()
    print(f"Time: {_t(t3, t0)} (walks: {_t(t1, t0)}, connections: {_t(t2, t1)})")


  async def _calc_stop_walks(self, osrm: OsrmClient):
    print("Calculating walking distances between stops")
    inputs = self.script("stop-walk/init").arrow()
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

      self.sql(
        "insert into stop_walk from result",
        views = {
          "result": pyarrow.table(
            [np.repeat(from_id, len(to_ids)), to_ids, distances],
            ["from_stop", "to_stop", "distance"],
          )
        },
      )


def _t(t_to, t_from):
  return f"{round(t_to - t_from, 3)}s"
