#!/usr/bin/env python3

import contextlib
import docker # type: ignore
import json
from pathlib import Path
import requests
import sys
import time
from typing import Iterable

SCRIPT_FOLDER = Path(__file__).parent
sys.path.append(str(SCRIPT_FOLDER.parent / "app"))

from bimba.transitdb import *
from bimba.unzip import *


DATA_FOLDER = SCRIPT_FOLDER.parent / "data" / "main"
OSRM_FOLDER = DATA_FOLDER / "osrm"
CITIES_FILE = SCRIPT_FOLDER / "cities.json"

OSRM_IMAGE = "ghcr.io/project-osrm/osrm-backend"
OSRM_PORT = 53909


def download_if_missing(url, path):
  if path.exists():
    return

  path.parent.mkdir(exist_ok=True, parents=True)
  print(f"Downloading '{url}' to '{path}'")
  content = requests.get(url).content

  with open(path, "wb") as file:
    file.write(content)


@contextlib.contextmanager
def start_osrm(data: Path):
  print(f"Starting osrm-routed on port {OSRM_PORT} (data: {data})")

  container = docker.from_env().containers.run(
    image=OSRM_IMAGE,
    command=f"osrm-routed --algorithm mld /data/map.osrm",
    volumes={str(data.absolute()): {"bind": "/data", "mode": "ro"}},
    ports={"5000/tcp": OSRM_PORT},
    detach=True,
    remove=True,
  )

  try:
    asyncio.run(osrm_healthcheck())
    yield
  finally:
    print("Stopping osrm-routed")
    container.stop()


async def osrm_healthcheck():
  osrm = OsrmClient(f"http://localhost:{OSRM_PORT}")

  # Wait for up to 30 seconds, check every 0.25 seconds
  for _ in range(30 * 4):
    if await osrm.healthcheck():
      return
    else:
      time.sleep(0.25)


def osrm_data(osm_url: str, folder: Path):
  if (folder / f"map.osrm.mldgr").exists():
    return

  osm_file = folder / "map.osm.pbf"
  download_if_missing(osm_url, osm_file)
  dc = docker.from_env()

  def osrm_backend(cmd):
    print(f"Running '{cmd}' in OSRM containter")

    dc.containers.run(
      image=OSRM_IMAGE,
      command=cmd,
      volumes={str(folder.absolute()): {"bind": "/data", "mode": "rw"}},
      remove=True,
    )

  osrm_backend(f"osrm-extract -p /opt/foot.lua /data/map.osm.pbf")
  osrm_backend(f"osrm-partition /data/map.osrm")
  osrm_backend(f"osrm-customize /data/map.osrm")


def prepare_city(city):
  for k, url in city["gtfs"].items():
    download_if_missing(url, DATA_FOLDER / f"{k}.zip")

  try:
    with TransitDb(DATA_FOLDER / "transit.db") as tdb:
      tdb.init_schema()

      for gtfs in city["gtfs"].keys():
        gtfs_zip = DATA_FOLDER / f"{gtfs}.zip"
        folder = gtfs_zip.parent / gtfs_zip.name.replace(".zip", "")
        unzip(gtfs_zip, folder)
        tdb.import_gtfs(folder)

      osrm_data(city["map"], OSRM_FOLDER)

      with start_osrm(OSRM_FOLDER):
        osrm = OsrmClient(f"http://localhost:{OSRM_PORT}")
        asyncio.run(tdb.calculate_stop_walks(osrm))

      tdb.finalize()

  except:
    (DATA_FOLDER / "transit.db").unlink(missing_ok=True)
    raise


if __name__ == "__main__":
  args = sys.argv
  cities = json.loads(CITIES_FILE.read_bytes())

  if len(args) == 1:
    print(f"Usage: {args[0]} CITY\nAvailable cities:")
    for city in cities.keys():
      print(f"  \"{city}\"")
  else:
    city_name = args[1]
    prepare_city(cities[city_name])
