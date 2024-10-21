import aiohttp
import contextlib
from itertools import chain
import numpy as np
from numpy.typing import NDArray
from typing import Iterable


class OsrmClient:
  base_url: str
  sessions: list[aiohttp.ClientSession]
  profile: str

  def __init__(self, url, profile = "foot"):
    self.base_url = url
    self.sessions = []
    self.profile = profile

  async def __aenter__(self):
    return self

  async def __aexit__(self, exc_type, exc, tb):
    await self.close()

  async def close(self):
    for s in self.sessions:
      await s.close()

  async def distance_to_many(
      self,
      from_lat: float,
      from_lon: float,
      to_pts: Iterable[tuple[float, float]],
    ) -> NDArray:
    def coords_parts():
      yield f"{from_lon},{from_lat}"

      for lat, lon in to_pts:
        yield f";{lon},{lat}"

    params = {"annotations": "distance", "sources": "0"}

    url = "".join(chain(
      f"/table/v1/{self.profile}/",
      coords_parts(),
    ))

    with self.__get_session() as session:
      async with session.get(url, params=params) as res:
        data = await res.json()

    from_snap = data["sources"][0]["distance"]
    dst = data["distances"][0][1:]
    destinations = data["destinations"][1:]
    count = len(destinations)

    return np.fromiter(
      (from_snap + dst[i] + destinations[i]["distance"] for i in range(0, count)),
      float,
      count,
    )

  @contextlib.contextmanager
  def __get_session(self):
    if len(self.sessions) == 0:
      session = aiohttp.ClientSession(self.base_url)
    else:
      session = self.sessions.pop()
    
    try:
      yield session
    finally:
      self.sessions.append(session)
