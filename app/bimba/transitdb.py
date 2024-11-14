import asyncio
from dataclasses import dataclass
import datetime
import duckdb
import functools
import numpy as np
from numpy.typing import NDArray
import os
from pathlib import Path
import pyarrow
import time
from typing import Iterable

from .data.common import Coords, Services
from .data.routes import Routes
from .data.shapes import Shapes
from .data.stops import Stops
from .data.trips import Trips
from .db import Db
from .osrm import OsrmClient
from ebus.algorithm_settings import WALKING_SETTINGS


class TransitDb(Db):
  OPTIONAL_GTFS_FILES = [
    "calendar.txt",
    "calendar_dates.txt",
    "feed_info.txt",
    "frequencies.txt",
  ]

  def __init__(self, path: Path, run_on_load: bool = True):
    scripts = Path(__file__).parent / "sql"
    variables = {
      "MAX_STOP_WALK": WALKING_SETTINGS["TIME_WITHIN_WALKING"] * WALKING_SETTINGS["PACE"]
    }

    super().__init__(path, scripts, variables)

    if run_on_load:
      self.script("on-load")


  def get_services(self, date: datetime.date) -> Services:
    s = self.sql("select get_service_lists(?)", [date]).scalar()

    return Services(
      np.array(s["today"], dtype=np.int32),
      np.array(s["yesterday"], dtype=np.int32),
      np.array(s["tomorrow"], dtype=np.int32),
    )


  def nearest_stops(self, coords: Coords) -> NDArray:
    params = {"lat": coords.lat, "lon": coords.lon}
    return self.script("get-nearest-stops", params).np()["id"]


  def get_routes(self) -> Routes:
    a = self.sql("select * from route order by id").arrow()
    ids, agencies, names, types, colors, text_colors = a.flatten()
    assert np.array_equal(ids, np.arange(len(a)))

    return Routes(
      agencies.to_numpy(),
      names.tolist(),
      types.to_numpy(),
      colors.to_numpy(),
      text_colors.to_numpy(),
    )


  def get_shapes(self) -> Shapes:
    a = self.sql("select * from shape order by id").arrow()
    ids, points = a.flatten()
    points_off = points.offsets
    points_lats, points_lons = points.values.flatten()
    assert np.array_equal(ids, np.arange(len(a)))

    return Shapes(
      points_off.to_numpy(),
      points_lats.to_numpy(),
      points_lons.to_numpy(),
    )


  def get_stops(self) -> Stops:
    a = self.sql("select * from stop order by id").arrow()
    ids, codes, names, zones, coords, positions, walks, trips = a.flatten()
    lats, lons = coords.flatten()
    xs, ys = positions.flatten()
    walks_off = walks.offsets
    walks_stop_ids, walks_distances = walks.values.flatten()
    trips_off = trips.offsets
    trips_ids, trips_seqs, trips_departures = trips.values.flatten()
    assert np.array_equal(ids, np.arange(len(a)))

    return Stops(
      codes.tolist(),
      names.tolist(),
      zones.tolist(),
      lats.to_numpy(),
      lons.to_numpy(),
      xs.to_numpy(),
      ys.to_numpy(),
      walks_off.to_numpy(),
      walks_stop_ids.to_numpy(),
      walks_distances.to_numpy(),
      trips_off.to_numpy(),
      trips_ids.to_numpy(),
      trips_seqs.to_numpy(),
      trips_departures.to_numpy(),
    )


  def get_trips(self) -> Trips:
    a = self.sql("select * from trip order by id").arrow()
    ids, routes, shapes, headsigns, first_departures, last_departures, instances, stops = a.flatten()
    instances_off = instances.offsets
    instances_services, instances_start_times, _ = instances.values.flatten()
    instances_services_off = instances_services.offsets
    instances_services = instances_services.values
    instances_start_times_off = instances_start_times.offsets
    instances_start_times = instances_start_times.values
    stops_off = stops.offsets
    stops_ids, stops_arrivals, stops_departures, _, _ = stops.values.flatten()
    assert np.array_equal(ids, np.arange(len(a)))

    return Trips(
      routes.to_numpy(),
      shapes.to_numpy(),
      headsigns.tolist(),
      first_departures.to_numpy(),
      last_departures.to_numpy(),
      instances_off.to_numpy(),
      instances_services_off.to_numpy(),
      instances_services.to_numpy(),
      instances_start_times_off.to_numpy(),
      instances_start_times.to_numpy(),
      stops_off.to_numpy(),
      stops_ids.to_numpy(),
      stops_arrivals.to_numpy(),
      stops_departures.to_numpy(),
    )


  def init_schema(self):
    print("Initializing schema")
    self.script("init")


  def import_gtfs(self, source_name: str, gtfs_folder: Path):
    print(f"Importing GTFS '{source_name}' from '{gtfs_folder}'")
    self.set_variable('SOURCE_NAME', source_name)
    self.set_variable('GTFS_FOLDER', str(gtfs_folder))

    t0 = time.time()
    self.script("gtfs/init")
    self.script("gtfs/import/required")

    for opt_gtfs in self.OPTIONAL_GTFS_FILES:
      if (gtfs_folder / opt_gtfs).exists():
        self.script(f"gtfs/import/{opt_gtfs[:-4].replace('_', '-')}")

    t1 = time.time()
    self.script("gtfs/process/assign-id")
    self.script("gtfs/process/services")
    self.script("gtfs/process/shapes")
    self.script("gtfs/process/trips")

    t2 = time.time()
    self.script("gtfs/insert")
    self.script("gtfs/clean-up")

    t3 = time.time()
    print(f"Time: {_t(t2, t0)} "
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
