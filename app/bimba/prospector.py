from itertools import chain
import numpy as np
import pyproj
from typing import NamedTuple

from .data.misc import Metadata, Point
from .data.stops import Stops
from .osrm import *
from .transitdb import TransitDb


class NearStop(NamedTuple):
  id: int
  walk_distance: float


class Prospect(NamedTuple):
  start: Point
  destination: Point
  walk_distance: float
  near_start: list[NearStop]
  near_destination: list[NearStop]


class Prospector:
  tdb: TransitDb
  osrm: OsrmClient
  md: Metadata
  stops: Stops
  transformer: pyproj.Transformer

  def __init__(self, tdb, osrm, md=None, stops=None, transformer=None):
    self.tdb = tdb
    self.osrm = osrm
    self.md = md or tdb.get_metadata()
    self.stops = stops or tdb.get_stops()
    self.transformer = transformer or pyproj.Transformer.from_proj('WGS84', self.md.projection)

  def clone(self):
    return Prospector(
      self.tdb.clone(),
      self.osrm,
      self.md,
      self.stops,
      self.transformer,
  )


  def prospect(
    self,
    start: Coords|int,
    destination: Coords|int,
  ) -> Prospect:
    if isinstance(start, Coords):
      start_coords = start
      start_point = self.project(start)
      near_start = None
    else:
      s = self.stops[start]
      start_coords = s.coords
      start_point = Point(np.float32(s.position.x), np.float32(s.position.y))
      near_start = [NearStop(np.int32(start), np.float32(0))]

    if isinstance(destination, Coords):
      destination_coords = destination
      destination_point = self.project(destination)
      near_destination = None
    else:
      s = self.stops[destination]
      destination_coords = s.coords
      destination_point = Point(np.float32(s.position.x), np.float32(s.position.y))
      near_destination = [NearStop(np.int32(destination), np.float32(0))]

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
      destination_point,
      walk_distance,
      near_start,
      near_destination,
    )


  def project(self, c: Coords) -> Point:
    x, y = self.transformer.transform(c.lat, c.lon)
    return Point(np.float32(x - self.md.center.x), np.float32(y - self.md.center.y))
