import numba as nb

@nb.jit
def inconvenience(
  walk_time = None,
  wait_time = None,
  transfer = False,
):
  value = 0

  if transfer:
    value += 1

  return value
