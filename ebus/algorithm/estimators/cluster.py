import numba as nb
import numpy as np
from pathlib import Path

from algorithm.estimator import *
from ebus.algorithm_settings import WALKING_SETTINGS


def cluster_estimator(clustertimes_path: Path) -> Estimator:
  clustertimes = np.load(clustertimes_path)
  uwdm = WALKING_SETTINGS["DISTANCE_MULTIPLIER"]
  pace = WALKING_SETTINGS["PACE"]

  @nb.jit
  def estimate(stops, prospect, from_stop, at_time):
    a = stops[from_stop]
    result = nb.int32(euclidean_metric(a.position, prospect.destination) * uwdm / pace)

    for near in prospect.near_destination:
      b = stops[near.id]
      ct = clustertimes[a.cluster, b.cluster]
      result = min(result, nb.int32(ct + nb.int32(near.walk_distance / pace)))

    return result

  return Estimator(estimate, INF_TIME)
