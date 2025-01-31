import datetime
import duckdb
import numpy as np
from numpy.typing import NDArray
from pathlib import Path

from .data.misc import *
from .data.routes import Routes
from .data.shapes import Shapes
from .data.stops import Stops
from .data.trips import Trips
from .db import Db


class TransitDb(Db):
  def __init__(self, path: Path, write=False):
    scripts = Path(__file__).parent / "transitdb-sql"
    super().__init__(path, scripts, write)
    self.sql("install spatial; load spatial")


  def clone(self):
    c = TransitDb.__new__(TransitDb)
    c.db = self.db.cursor()
    c.scripts = self.scripts
    return c


  def get_services(self, date: datetime.date) -> Services:
    s = self.sql("select get_service_lists(?)", [date]).scalar()

    return Services(
      np.array(s["today"], dtype=np.int32),
      np.array(s["yesterday"], dtype=np.int32),
      np.array(s["tomorrow"], dtype=np.int32),
    )


  def nearest_stops(self, position: Point, radius: float, min_count: int) -> NDArray:
    params = {
      "x": float(position.x),
      "y": float(position.y),
      "radius": radius,
      "min_count": min_count,
    }

    return self.script("get-nearest-stops", params).np()["id"]


  def get_metadata(self) -> Metadata:
    md = self.sql("select metadata from metadata").scalar()
    md["center_coords"] = Coords(**md["center_coords"])
    md["center_position"] = Point(**md["center_position"])
    return Metadata(**md)


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
    ids, codes, names, zones, clusters, coords, positions, walks, trips = a.flatten()
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
      clusters.to_numpy(),
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
    ids, routes, shapes, headsigns, first_departures, last_departures, starts, stops = a.flatten()
    starts_off = starts.offsets
    starts_services, starts_times = starts.values.flatten()
    starts_services_off = starts_services.offsets
    starts_services = starts_services.values
    starts_times_off = starts_times.offsets
    starts_times = starts_times.values
    stops_off = stops.offsets
    stops_ids, stops_arrivals, stops_departures, _, _ = stops.values.flatten()
    assert np.array_equal(ids, np.arange(len(a)))

    return Trips(
      routes.to_numpy(),
      shapes.fill_null(-1).to_numpy(),
      headsigns.tolist(),
      first_departures.to_numpy(),
      last_departures.to_numpy(),
      starts_off.to_numpy(),
      starts_services_off.to_numpy(),
      starts_services.to_numpy(),
      starts_times_off.to_numpy(),
      starts_times.to_numpy(),
      stops_off.to_numpy(),
      stops_ids.to_numpy(),
      stops_arrivals.to_numpy(),
      stops_departures.to_numpy(),
    )


  def get_trip_instance(self, trip: int, service: int, start_time: int) -> TripInstance:
    wa, id = self.sql("""
      select wheelchair_accessible, gtfs_trip_id
      from trip_instance
      where trip = ? and service = ? and start_time = ?
    """, [trip, service, start_time]).one()

    return TripInstance(wa, id)


  def process_delays(self, trip_updates: str) -> Delays:
    res = self.script("process-delays", [trip_updates])

    if res.count() == 0:
      return Delays.empty()

    trip_ids, services, start_times, delays = res.arrow().flatten()

    return Delays(
      trip_ids.to_numpy(),
      services.to_numpy(),
      start_times.to_numpy(),
      delays.to_numpy(),
    )
