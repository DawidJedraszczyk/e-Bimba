import aiohttp
import contextlib
from itertools import chain
import numpy as np
from numpy.typing import NDArray
import requests
from typing import Iterable

from .data.misc import Coords


class OsrmClient:
  base_url: str
  profile: str

  def __init__(self, url, profile = "foot"):
    self.base_url = url
    self.profile = profile


  def call(self, url, params={}):
    return requests.get(self.base_url + url, params).json()


  async def call_async(self, url, params={}):
    async with aiohttp.ClientSession(self.base_url) as session:
      async with session.get(url, params=params) as res:
        return await res.json()


  def distance_to_many(
    self,
    a: Coords,
    bs: Iterable[Coords],
  ) -> NDArray:
    return self.dtm_end(self.call(*self.dtm_beg(a, bs)))


  async def distance_to_many_async(
    self,
    a: Coords,
    bs: Iterable[Coords],
  ) -> NDArray:
    return self.dtm_end(await self.call_async(*self.dtm_beg(a, bs)))


  def dtm_beg(self, a, bs):
    def coords_parts():
      yield f"{a.lon},{a.lat}"

      for b in bs:
        yield f";{b.lon},{b.lat}"

    params = {"annotations": "distance", "sources": "0"}

    url = "".join(chain(
      f"/table/v1/{self.profile}/",
      coords_parts(),
    ))

    return (url, params)


  def dtm_end(self, data):
    from_snap = data["sources"][0]["distance"]
    dst = data["distances"][0][1:]
    destinations = data["destinations"][1:]
    count = len(destinations)

    return np.fromiter(
      (from_snap + dst[i] + destinations[i]["distance"] for i in range(0, count)),
      np.float32,
      count,
    )


  def healthcheck(self) -> bool:
    try:
      self.call(f"/nearest/v1/{self.profile}/0,0.json")
      return True
    except:
      return False
