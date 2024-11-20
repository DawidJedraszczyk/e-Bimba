# Based on stdlib's heapq, modified to keep track of heap position inside queue item.

import numba as nb


@nb.jit
def _siftdown(heap, startpos, pos, item):
  while pos > startpos:
    parentpos = (pos - 1) >> 1
    parent = heap[parentpos]

    if item < parent:
      heap[pos] = parent
      parent.heap_pos = pos
      pos = parentpos
    else:
      break

  heap[pos] = item
  item.heap_pos = pos


@nb.jit
def _siftup(heap, pos, item):
  endpos = len(heap)
  startpos = pos
  childpos = 2 * pos + 1

  while childpos < endpos:
    rightpos = childpos + 1

    if rightpos < endpos and not heap[childpos] < heap[rightpos]:
      childpos = rightpos

    child = heap[childpos]
    heap[pos] = child
    child.heap_pos = pos
    pos = childpos
    childpos = 2 * pos + 1

  _siftdown(heap, startpos, pos, item)


@nb.jit
def heapify(heap):
  for i in range((len(heap) // 2) - 1, -1, -1):
    _siftup(heap, i, heap[i])

  for i in range(len(heap) // 2, len(heap)):
    heap[i].heap_pos = i


@nb.jit
def heappush(heap, item):
  pos = len(heap)
  heap.append(item)
  _siftdown(heap, 0, pos, item)


@nb.jit
def heappop(heap):
  lastelt = heap.pop()

  if heap:
    returnitem = heap[0]
    returnitem.heap_pos = -1
    _siftup(heap, 0, lastelt)
    return returnitem

  lastelt.heap_pos = -1
  return lastelt


@nb.jit
def heapdec(heap, item):
  _siftdown(heap, 0, item.heap_pos, item)
