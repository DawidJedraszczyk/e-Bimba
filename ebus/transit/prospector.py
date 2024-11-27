from itertools import chain
import numpy as np
import pyproj
from typing import NamedTuple, Optional

from .data.misc import Coords, Metadata, Point
from .data.stops import Stops
from .osrm import *
from .transitdb import TransitDb


class NearStop(NamedTuple):
  id: int
  walk_distance: float


class Prospect(NamedTuple):
  start: Point
  start_coords: Coords
  near_start: list[NearStop]

  destination: Point
  destination_coords: Coords
  near_destination: list[NearStop]

  walk_distance: float


class Prospector:
  tdb: TransitDb
  osrm: OsrmClient
  md: Metadata
  stops: Stops
  transformer: pyproj.Transformer
  untransformer: pyproj.Transformer

  def __init__(self, tdb, osrm, md=None, stops=None, transformer=None, untransformer=None):
    self.tdb = tdb
    self.osrm = osrm
    self.md = md or tdb.get_metadata()
    self.stops = stops or tdb.get_stops()
    self.transformer = transformer or pyproj.Transformer.from_proj('WGS84', self.md.projection)
    self.untransformer = untransformer or pyproj.Transformer.from_proj(self.md.projection, 'WGS84')

  def clone(self):
    return Prospector(
      self.tdb.clone(),
      self.osrm,
      self.md,
      self.stops,
      self.transformer,
      self.untransformer,
  )


  def prospect(
    self,
    start: Coords|Point|int,
    destination: Coords|Point|int,
  ) -> Prospect:
    start_coords, start_point, near_start = self.standardize(start)
    destination_coords, destination_point, near_destination = self.standardize(destination)
    walk_distance = None

    if near_start is None:
      ns_ids = self.tdb.nearest_stops(start_point)

      distances = self.osrm.distance_to_many(
        start_coords,
        chain((self.stops[id].coords for id in ns_ids), [destination_coords]),
      )

      near_start = [NearStop(id, dst) for id, dst in zip(ns_ids, distances)]
      walk_distance = distances[-1]

    if near_destination is None:
      nd_ids = self.tdb.nearest_stops(destination_point)
      to_coords = [self.stops[id].coords for id in nd_ids]

      if walk_distance is None:
        to_coords.append(start_coords)

      distances = self.osrm.distance_to_many(destination_coords, to_coords)
      near_destination = [NearStop(id, dst) for id, dst in zip(nd_ids, distances)]

      if walk_distance is None:
        walk_distance = distances[-1]

    if walk_distance is None:
      distances = self.osrm.distance_to_many(start_coords, [destination_coords])
      walk_distance = distances[0]

    return Prospect(
      start_point,
      start_coords,
      near_start,
      destination_point,
      destination_coords,
      near_destination,
      walk_distance,
    )


  def project(self, c: Coords) -> Point:
    x, y = self.transformer.transform(c.lat, c.lon)

    return Point(
      np.float32(x - self.md.center_position.x),
      np.float32(y - self.md.center_position.y)
    )


  def unproject(self, p: Point) -> Coords:
    x = p.x + self.md.center.x
    y = p.y + self.md.center.y
    lat, lon = self.untransformer.transform(x, y)
    return Coords(np.float32(lat), np.float32(lon))


  def standardize(
    self,
    location: Coords|Point|int,
  ) -> tuple[
    Coords,
    Point,
    Optional[list[NearStop]]
  ]:
    if isinstance(location, Coords):
      coords = location
      point = self.project(location)
      near = None
    elif isinstance(location, Point):
      coords = self.unproject(location)
      point = location
      near = None
    elif isinstance(location, int):
      s = self.stops[location]
      coords = Coords(np.float32(s.coords.lat), np.float32(s.coords.lon))
      point = Point(np.float32(s.position.x), np.float32(s.position.y))
      near = [NearStop(np.int32(location), np.float32(0))]
    else:
      raise Exception(f"Prospector.standardize: unsupported argument type {type(location)}")

    return coords, point, near
