import time
import math
import numba as nb
import numpy as np
from pathlib import Path
from typing import Callable

from algorithm.estimator import *
from transit.data.misc import INF_TIME, Point
from transit.data.stops import Stops
from algorithm.utils import custom_print
try:
  from ai_edge_litert.interpreter import Interpreter
except:
  from tensorflow.lite.python.interpreter import Interpreter


def nn_estimator(file: Path, stops: Stops) -> Estimator:
  interpreter = Interpreter(model_content=file.read_bytes())
  in_idx = interpreter.get_input_details()[0]["index"]
  out_idx = interpreter.get_output_details()[0]["index"]

  interpreter.resize_tensor_input(in_idx, (1, 6))
  interpreter.allocate_tensors()

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

    interpreter.set_tensor(in_idx, inputs)
    interpreter.invoke()
    output = interpreter.get_tensor(out_idx)

    result = output[0, 0]
    if result > 21600:
        custom_print("NN result big", 'WARNINGS')
        return 21600
    else:
        return int(output[0, 0])

  return Estimator(estimate, 0)


def nn_ref_estimator(file: Path, stops: Stops, reference: Estimator) -> Estimator:
  interpreter = Interpreter(model_content=file.read_bytes())
  in_idx = interpreter.get_input_details()[0]["index"]
  out_idx = interpreter.get_output_details()[0]["index"]

  interpreter.resize_tensor_input(in_idx, (1, 7))
  interpreter.allocate_tensors()

  x_scale = 1 / np.std(stops.xs)
  y_scale = 1 / np.std(stops.ys)
  time_scale = 1 / (24*60*60)
  reference = reference.estimate

  def estimate(stops, prospect, from_stop, at_time):
    from_x, from_y = stops[from_stop].position
    to_x, to_y = prospect.destination
    day_type, start_time = at_time
    ref = reference(stops, prospect, from_stop, at_time)

    inputs = np.array(
      [[
        from_x * x_scale,
        from_y * y_scale,
        to_x * x_scale,
        to_y * y_scale,
        day_type,
        start_time * time_scale,
        ref,
      ]],
      dtype=np.float32,
    )

    interpreter.set_tensor(in_idx, inputs)
    interpreter.invoke()
    output = interpreter.get_tensor(out_idx)[0]
    return int(0.8*output + 0.2*ref)

  return Estimator(estimate, 0)
