import contextlib
import docker
import json
from pathlib import Path
import time

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


def fpath(path: Path):
  return str(path.relative_to(ROOT))


@contextlib.contextmanager
def start_osrm(region: str):
  print(f"Starting osrm-routed {fpath(DATA_REGIONS / region)} on port {OSRM_PORT}")

  container = docker.from_env().containers.run(
    image=OSRM_IMAGE,
    command=f"osrm-routed --algorithm mld /data/map.osrm",
    volumes={str((DATA_REGIONS / region).absolute()): {"bind": "/data", "mode": "ro"}},
    ports={"5000/tcp": OSRM_PORT},
    detach=True,
    remove=True,
  )

  try:
    osrm = OsrmClient(f"http://localhost:{OSRM_PORT}")
    osrm_healthcheck(osrm)
    yield osrm
  finally:
    print("Stopping osrm-routed")
    container.stop()


def osrm_healthcheck(osrm):
  # Wait for up to 30 seconds, check every 0.25 seconds
  for _ in range(30 * 4):
    if osrm.healthcheck():
      return
    else:
      time.sleep(0.25)
