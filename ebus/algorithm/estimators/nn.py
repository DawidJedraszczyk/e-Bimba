import time
import math
import numba as nb
import numpy as np
from pathlib import Path
from typing import Callable

from algorithm.estimator import *
from transit.data.misc import INF_TIME, Point

try:
  from ai_edge_litert.interpreter import Interpreter
except:
  from tensorflow.lite.python.interpreter import Interpreter


def nn_estimator(file: Path) -> Estimator:
  with open(str(file), 'rb') as f:
    tflite_model = f.read()

  interpreter = Interpreter(model_content=tflite_model)
  interpreter.allocate_tensors()

  in_idx = interpreter.get_input_details()[0]["index"]
  out_idx = interpreter.get_output_details()[0]["index"]

  def inference(from_point, to_point, day_type, daytime):
    inputs = np.array(
      [[from_point.x, from_point.y, to_point.x, to_point.y, day_type, daytime]],
      dtype=np.float64,
    )

    interpreter.set_tensor(in_idx, inputs)
    interpreter.invoke()
    output = interpreter.get_tensor(out_idx)[0, 0]

    if output < 0:
      return 0
    elif math.isinf(output):
      return INF_TIME
    else:
      return int(output)

  def estimate(stops, prospect, from_stop, at_time):
    return inference(stops[from_stop].position, prospect.destination, *at_time)

  def stop_to_stop(stops, a, b, at_time):
    return inference(stops[a].position, stops[b].position, *at_time)

  return Estimator(estimate, stop_to_stop, 0)
