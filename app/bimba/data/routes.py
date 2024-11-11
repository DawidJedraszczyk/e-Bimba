import numba as nb
import numba.types as nbt
from numba.experimental import jitclass
from typing import NamedTuple

from .common import *


class Route(NamedTuple):
  agency_id: int
  name: str
  type: int
  color: int
  text_color: int


@jitclass([
  ("agency_ids", nb.int32[:]),
  ("names", nbt.List(nbt.string)),
  ("types", nb.int8[:]),
  ("colors", nb.int32[:]),
  ("text_colors", nb.int32[:]),
])
class Routes:
  def __init__(
    self,
    agency_ids,
    names,
    types,
    colors,
    text_colors,
  ):
    self.agency_ids = agency_ids
    self.names = names
    self.types = types
    self.colors = colors
    self.text_colors = text_colors

  def __getitem__(self, id: int) -> Route:
    return Route(
      self.agency_ids[id],
      self.names[id],
      self.types[id],
      self.colors[id],
      self.text_colors[id],
    )

  def get_route(self, id: int) -> Route:
    return self[id]
