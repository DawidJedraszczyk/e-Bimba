import aiohttp
import contextlib
from itertools import chain
import numpy as np
from numpy.typing import NDArray
from typing import Iterable

from .data.common import Coords


class OsrmClient:
  base_url: str
  profile: str

  def __init__(self, url, profile = "foot"):
    self.base_url = url
    self.profile = profile


  async def distance_to_many(
    self,
    a: Coords,
    bs: Iterable[Coords],
  ) -> NDArray:
    def coords_parts():
      yield f"{a.lon},{a.lat}"

      for b in bs:
        yield f";{b.lon},{b.lat}"

    params = {"annotations": "distance", "sources": "0"}

    url = "".join(chain(
      f"/table/v1/{self.profile}/",
      coords_parts(),
    ))

    async with aiohttp.ClientSession(self.base_url) as session:
      async with session.get(url, params=params) as res:
        data = await res.json()

    from_snap = data["sources"][0]["distance"]
    dst = data["distances"][0][1:]
    destinations = data["destinations"][1:]
    count = len(destinations)

    return np.fromiter(
      (from_snap + dst[i] + destinations[i]["distance"] for i in range(0, count)),
      np.float32,
      count,
    )


  async def healthcheck(self) -> bool:
    try:
      async with aiohttp.ClientSession(self.base_url) as session:
        async with session.get(f"/nearest/v1/{self.profile}/0,0.json") as res:
          await res.json()
          return True
    except:
      return False
