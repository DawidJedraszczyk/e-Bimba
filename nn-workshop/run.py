#!/usr/bin/env python3

import contextlib
import docker # type: ignore
import json
from pathlib import Path
import requests
import sys
from typing import Iterable

from lib.transitdb import *
from lib.unzip import *


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
    yield
  finally:
    print("Stopping osrm-routed")
    container.stop()


def import_gtfs(zips: Iterable[Path], tdb_path: Path):
  with TransitDb(tdb_path) as tdb:
    tdb.init_schema()

    for gtfs_zip in zips:
      folder = gtfs_zip.parent / gtfs_zip.name.replace(".zip", "")
      unzip(gtfs_zip, folder)
      tdb.import_gtfs(folder)


def generate_connections(tdb_path: Path, osrm_data: Path):
  with (
    start_osrm(osrm_data),
    TransitDb(tdb_path) as tdb,
  ):
    osrm = OsrmClient(f"http://localhost:{OSRM_PORT}")
    asyncio.run(tdb.generate_connections(osrm))


def osrm_data(osm_url: str, folder: Path):
  if (folder / f"map.osrm.fileIndex").exists():
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


def city(cities, name):
  city = cities["cities"][name]
  workdir = Path(city["workdir"])
  region = cities["osrm"][city["osrm"]]

  osrm_workdir = Path(region["workdir"])
  osrm_data(region["map"], osrm_workdir)

  for k, url in city["gtfs"].items():
    download_if_missing(url, workdir / f"{k}.zip")

  import_gtfs(
    [workdir / f"{k}.zip" for k in city["gtfs"].keys()],
    workdir / "transit.db"
  )

  generate_connections(workdir / "transit.db", osrm_workdir)


if __name__ == "__main__":
  args = sys.argv[1:]

  if len(args) == 0:
    print(
      "Commands:\n"
      "  import GTFS_ZIP... TRANSIT_DB\n"
      "  connections TRANSIT_DB OSRM_DATA\n"
      "  osrm_data OSM_URL FOLDER\n"
      "  CITIES_JSON CITY\n"
    )
    sys.exit()

  match args[0]:
    case "import":
      zips = [Path(s) for s in args[1:-1]]
      tdb_path = Path(args[-1])
      import_gtfs(zips, tdb_path)

    case "connections":
      tdb_path = Path(args[1])
      osrm_data = Path(args[2])
      generate_connections(tdb_path, osrm_data)

    case "osrm_data":
      osm_url = args[1]
      folder = Path(args[2])
      osrm_data(osm_url, folder)

    case _ if args[0].endswith(".json"):
      cities_file = Path(args[0])
      city_name = args[1]
      cities = json.loads(cities_file.read_bytes())
      city(cities, city_name)
