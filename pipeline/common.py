import contextlib
import docker
import json
from pathlib import Path
import shutil
import subprocess
import time
import zipfile

from transit.osrm import OsrmClient


PIPELINE = Path(__file__).parent
ROOT = PIPELINE.parent
DATA = ROOT / "data"
DATA_CITIES = DATA / "cities"
DATA_REGIONS = DATA / "regions"
TMP = PIPELINE / "tmp"
TMP_CITIES = TMP / "cities"
TMP_REGIONS = TMP / "regions"

CITIES = json.loads((ROOT / "cities.json").read_bytes())
REGIONS = json.loads((ROOT / "regions.json").read_bytes())

OSRM_IMAGE = "ghcr.io/project-osrm/osrm-backend"
OSRM_PORT = 53909

FUSE_ZIP = "fuse-zip"

OPTIONAL_GTFS_FILES = [
  "calendar.txt",
  "calendar_dates.txt",
  "feed_info.txt",
  "frequencies.txt",
]


def fpath(path: Path):
  return str(path.relative_to(ROOT))


def get_city(name_or_id):
  for city in CITIES:
    if city["name"] == name_or_id or city["id"] == name_or_id:
      return city

  return None


def unzip(file: Path, folder: Path):
  if folder.exists():
    if next(folder.iterdir(), None) is not None:
      print(f"Folder '{fpath(folder)}' is not empty, assuming alread unzipped")
      return

    print(f"Removing empty folder '{fpath(folder)}'")
    folder.rmdir()

  if shutil.which(FUSE_ZIP) is not None:
    try:
      print(f"Mounting '{fpath(file)}' as '{fpath(folder)}' using {FUSE_ZIP}")
      folder.mkdir()
      subprocess.run([FUSE_ZIP, "-r", file, folder], check=True)
      return
    except Exception as e:
      print(f"Failed ({e})")
      folder.rmdir()

  print(f"Unzipping '{fpath(file)}' to '{fpath(folder)}'")

  with zipfile.ZipFile(file, "r") as zip:
    zip.extractall(folder)


@contextlib.contextmanager
def start_osrm(region: str, instances=1):
  d = docker.from_env()
  ports = [OSRM_PORT + i for i in range(instances)]
  print(f"Starting {instances} osrm-routed {fpath(DATA_REGIONS / region)} on ports {ports}")

  containers = [
    d.containers.run(
      image=OSRM_IMAGE,
      command=f"osrm-routed --algorithm mld /data/map.osrm",
      volumes={str((DATA_REGIONS / region).absolute()): {"bind": "/data", "mode": "ro"}},
      ports={"5000/tcp": port},
      detach=True,
      remove=True,
    )
    for port in ports
  ]

  try:
    osrm = OsrmClient([f"http://localhost:{port}" for port in ports], retry=True)
    osrm_healthcheck(osrm)
    yield osrm
  finally:
    print("Stopping osrm-routed")
    for c in containers:
      c.stop()


def osrm_healthcheck(osrm):
  # Wait for up to 30 seconds, check every 0.25 seconds
  for _ in range(30 * 4):
    if osrm.healthcheck():
      return
    else:
      time.sleep(0.25)
