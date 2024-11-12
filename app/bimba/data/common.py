import numba as nb
from numba.experimental import jitclass
import numpy as np
from typing import NamedTuple


DAY = 24*60*60
INF_TIME = 0x1FFFFFFF


class Point(NamedTuple):
  x: float
  y: float

class Coords(NamedTuple):
  lat: float
  lon: float

class Range(NamedTuple):
  beg: int
  end: int


@jitclass([
  ("today", nb.int32[:]),
  ("yesterday", nb.int32[:]),
  ("tomorrow", nb.int32[:]),
])
class Services:
  def __init__(self, today, yesterday, tomorrow):
    self.today = today
    self.yesterday = yesterday
    self.tomorrow = tomorrow

    self.today.sort()
    self.yesterday.sort()
    self.tomorrow.sort()
