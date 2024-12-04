import numba as nb
import numpy as np
from pathlib import Path

from algorithm.estimator import *


def cluster_estimator(clustertimes_path: Path) -> Estimator:
  clustertimes = np.load(clustertimes_path)

  def estimate(stops, prospector, from_stop, at_time):
    raise Exception("missing")

  @nb.jit
  def stop_to_stop(stops, a, b, at_time):
    return clustertimes[stops[a].cluster, stops[b].cluster]

  return via_nearest(Estimator(estimate, stop_to_stop, INF_TIME))
