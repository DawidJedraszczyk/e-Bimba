import aiohttp
import asyncio
import contextlib
from itertools import chain
import math
import numpy as np
from numpy.typing import NDArray
import random
import requests
from time import sleep
from typing import Iterable

from .data.misc import Coords


class OsrmClient:
  instances: list[str]
  profile: str
  retry: bool

  def __init__(self, url, profile="foot", retry=False):
    self.instances = [url] if isinstance(url, str) else url
    self.profile = profile
    self.retry = retry


  def call(self, url, params={}):
    while True:
      try:
        return requests.get(self.get_instance() + url, params).json()
      except Exception as ex:
        if self.retry:
          print(ex)
          sleep(random.random())
          continue
        else:
          raise


  async def call_async(self, url, params={}):
    while True:
      try:
        async with aiohttp.ClientSession(self.get_instance()) as session:
          async with session.get(url, params=params) as res:
            return await res.json()
      except Exception as ex:
        if self.retry:
          print(ex)
          await asyncio.sleep(random.random())
          continue
        else:
          raise


  def get_instance(self):
    return random.choice(self.instances)


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
      (from_snap + (dst[i] or math.inf) + destinations[i]["distance"] for i in range(0, count)),
      np.float32,
      count,
    )


  def nearest(self, coords: Coords) -> Coords:
    res = self.call(f"/nearest/v1/{self.profile}/{coords.lon},{coords.lat}.json")
    loc = res["waypoints"][0]["location"]
    return Coords(np.float32(loc[1]), np.float32(loc[0]))


  def healthcheck(self) -> bool:
    try:
      for instance in self.instances:
        requests.get(f"{instance}/nearest/v1/{self.profile}/0,0.json").json()

      return True
    except:
      return False
