from ai_edge_litert.interpreter import Interpreter
import math
import numpy as np
from pathlib import Path
from typing import Callable

from transit.data.misc import INF_TIME, Point


def load_nn(file: Path) -> Callable[[Point, Point, int, int], int]:
  interpreter = Interpreter(model_path=str(file))
  interpreter.allocate_tensors()

  in_idx = interpreter.get_input_details()[0]["index"]
  out_idx = interpreter.get_output_details()[0]["index"]

  def inference(from_point, to_point, day_type, time):
    inputs = np.array(
      [[from_point.x, from_point.y, to_point.x, to_point.y, day_type, time]],
      dtype=np.float32,
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

  return inference
