#!/usr/bin/env python3

import docker
import json
from pathlib import Path
import requests
import sys
import time
from typing import Iterable

sys.path.append(str(Path(__file__).parents[1] / "ebus"))
sys.path.append(str(Path(__file__).parent))

from common import *
from bimba.osrm import *
from bimba.transitdb import *
from bimba.unzip import *


CITIES_FILE = PIPELINE / "cities.json"


def download_if_missing(url, path):
  if path.exists():
    return

  path.parent.mkdir(exist_ok=True, parents=True)
  print(f"Downloading '{url}' to '{path}'")
  content = requests.get(url).content

  with open(path, "wb") as file:
    file.write(content)


def osrm_data(osm_url: str):
  if (OSRM_FOLDER / f"map.osrm.mldgr").exists():
    return

  osm_file = OSRM_FOLDER / "map.osm.pbf"
  download_if_missing(osm_url, osm_file)
  dc = docker.from_env()

  def osrm_backend(cmd):
    print(f"Running '{cmd}' in OSRM containter")

    dc.containers.run(
      image=OSRM_IMAGE,
      command=cmd,
      volumes={str(OSRM_FOLDER.absolute()): {"bind": "/data", "mode": "rw"}},
      remove=True,
    )

  osrm_backend(f"osrm-extract -p /opt/foot.lua /data/map.osm.pbf")
  osrm_backend(f"osrm-partition /data/map.osrm")
  osrm_backend(f"osrm-customize /data/map.osrm")


def prepare_city(city, name):
  for k, url in city["gtfs"].items():
    download_if_missing(url, DATA_FOLDER / f"{k}.zip")

  try:
    with TransitDb(DATA_FOLDER / "transit.db", run_on_load = False) as tdb:
      tdb.set_variable("PROJECTION", city["projection"])
      tdb.set_variable("CITY", name)
      tdb.init_schema()

      for gtfs in city["gtfs"].keys():
        gtfs_zip = DATA_FOLDER / f"{gtfs}.zip"
        folder = gtfs_zip.parent / gtfs_zip.name.replace(".zip", "")
        unzip(gtfs_zip, folder)
        tdb.import_gtfs(gtfs, folder)

      osrm_data(city["map"])

      with start_osrm():
        osrm = OsrmClient(f"http://localhost:{OSRM_PORT}")
        asyncio.run(tdb.calculate_stop_walks(osrm))

      tdb.finalize()

  except:
    (DATA_FOLDER / "transit.db").unlink(missing_ok=True)
    raise


def main():
  args = sys.argv
  cities = json.loads(CITIES_FILE.read_bytes())

  if len(args) == 1:
    print(f"Usage: {args[0]} CITY")
  else:
    city_name = " ".join(args[1:])

    if city_name not in cities:
      print(f"Unknown city '{city_name}'")
    else:
      prepare_city(cities[city_name], city_name)
      return

  print("Available cities:")

  for city in cities.keys():
    print(f"  {city}")


if __name__ == "__main__":
  main()
