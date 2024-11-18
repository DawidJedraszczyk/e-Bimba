from haversine.haversine import _haversine_kernel
import math
import numba as nb
from numba.experimental import jitclass

from .misc import *


@jitclass([
  ("points_off", nb.int32[:]),
  ("points_lats", nb.float32[:]),
  ("points_lons", nb.float32[:]),
])
class Shapes:
  def __init__(
    self,
    points_off,
    points_lats,
    points_lons,
  ):
    self.points_off = points_off
    self.points_lats = points_lats
    self.points_lons = points_lons


  def __getitem__(self, id: int) -> list[Coords]:
    return [
      Coords(self.points_lats[i], self.points_lons[i])
      for i in range(self.points_off[id], self.points_off[id+1])
    ]


  def get_shape(self, id: int) -> list[Coords]:
    return self[id]


  def get_points_between(self, shape_id: int, a: Coords, b: Coords) -> list[Coords]:
    points = self[shape_id]
    a_min = math.inf
    a_idx = 0
    b_min = math.inf
    b_idx = 0

    for i in range(len(points)):
      p = points[i]
      a_distance = _haversine_kernel(a.lat, a.lon, p.lat, p.lon)
      b_distance = _haversine_kernel(b.lat, b.lon, p.lat, p.lon)

      if a_distance < a_min:
        a_min = a_distance
        a_idx = i
      
      if b_distance < b_min:
        b_min = b_distance
        b_idx = i
    
    beg = min(a_idx, b_idx)
    end = max(a_idx, b_idx) + 1
    return points[beg:end]
