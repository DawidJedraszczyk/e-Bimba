import numba as nb
import numpy as np
from pathlib import Path

from algorithm.estimator import *
from transit.data.stops import Stops
from transit.knndb import KnnDb

N = 5

def knn_estimator(knndb: KnnDb|Path, stops: Stops) -> Estimator:
  if isinstance(knndb, Path):
    knndb = KnnDb(knndb)

  x_scale = 1 / np.std(stops.xs)
  y_scale = 1 / np.std(stops.ys)
  time_scale = 1 / (24*60*60)

  def estimate(stops, prospect, from_stop, at_time):
    from_x, from_y = stops[from_stop].position
    to_x, to_y = prospect.destination
    day_type, start_time = at_time

    inputs = np.array(
      [
        from_x * x_scale,
        from_y * y_scale,
        to_x * x_scale,
        to_y * y_scale,
        day_type,
        start_time * time_scale,
      ],
      dtype=np.float32,
    )

    return min(knndb.search(inputs, N))

  return Estimator(estimate, 0)
