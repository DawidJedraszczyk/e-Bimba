import numba as nb
import numpy as np
from pathlib import Path
from sklearn.neighbors import KNeighborsRegressor
import pickle

from algorithm.estimator import *
from transit.data.stops import Stops


def knn_estimator(knn: KNeighborsRegressor|Path, stops: Stops) -> Estimator:
  if isinstance(knn, Path):
    with knn.open("rb") as file:
      knn = pickle.load(file)

  assert isinstance(knn, KNeighborsRegressor)
  x_scale = 1 / np.std(stops.xs)
  y_scale = 1 / np.std(stops.ys)
  time_scale = 1 / (24*60*60)

  def estimate(stops, prospect, from_stop, at_time):
    from_x, from_y = stops[from_stop].position
    to_x, to_y = prospect.destination
    day_type, start_time = at_time

    inputs = np.array(
      [[
        from_x * x_scale,
        from_y * y_scale,
        to_x * x_scale,
        to_y * y_scale,
        day_type,
        start_time * time_scale,
      ]],
      dtype=np.float32,
    )

    indices = knn.kneighbors(inputs, return_distance=False)[0]
    return knn._y[indices].min()

  return Estimator(estimate, 0)
