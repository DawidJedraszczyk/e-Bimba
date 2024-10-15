#!/usr/bin/env python3

import atexit
from concurrent.futures import ThreadPoolExecutor
import contextlib
import docker
import duckdb
import os
import numpy as np
import math
import pandas as pd
from pathlib import Path
import requests
import threading
import time
import zipfile


DATASET_SIZE_TRAIN = int(1e7)
DATASET_SIZE_VALID = int(5e5)

ROOT = Path(__file__).parent
DATA = ROOT / "data"
SQL = ROOT / "sql"
TRANSIT_DB = DATA / "transit.db"
WALKD_TRAIN_DB = DATA / "walks-train.db"
WALKD_VALID_DB = DATA / "walks-valid.db"
TMP_DB = DATA / "tmp.db"
GTFS_ZIP = DATA / "gtfs.zip"
GTFS_DIR = DATA / "gtfs"
OSRM_FOLDER = DATA / "osrm"
MAP_NAME = "map"
OSM_FILE = OSRM_FOLDER / f"{MAP_NAME}.osm.pbf"

GTFS_URL = "https://www.ztm.poznan.pl/pl/dla-deweloperow/getGTFSFile"
OSM_URL = "http://download.geofabrik.de/europe/poland/wielkopolskie-latest.osm.pbf"

OSRM_IMAGE = "ghcr.io/project-osrm/osrm-backend"
OSRM_PORT = 53909
OSRM_TABLE_BATCH = 100
OSRM_TABLE_OUTPUT = OSRM_TABLE_BATCH * (OSRM_TABLE_BATCH - 1) / 2

osrm_container = None
threadpool_handle: ThreadPoolExecutor = None


def download_if_missing(url, path):
    if path.exists():
        return

    path.parent.mkdir(exist_ok=True)
    print(f"Downloading '{url}' to '{path.relative_to(Path.cwd())}'")
    content = requests.get(url).content

    with open(path, "wb") as file:
        file.write(content)


def get_gtfs():
    if GTFS_DIR.exists():
        return

    download_if_missing(GTFS_URL, GTFS_ZIP)

    with zipfile.ZipFile(GTFS_ZIP, "r") as zip:
        zip.extractall(GTFS_DIR)


def prepare_osrm():
    if (OSRM_FOLDER / f"{MAP_NAME}.osrm.fileIndex").exists():
        return

    download_if_missing(OSM_URL, OSM_FILE)

    volume = {str(DATA / "osrm"): {"bind": "/data", "mode": "rw"}}
    source = f"/data/{OSM_FILE.relative_to(OSRM_FOLDER)}"
    dc = docker.from_env()

    def osrm_backend(cmd):
        print(f"Running '{cmd}' in OSRM containter")

        dc.containers.run(
            image=OSRM_IMAGE,
            command=cmd,
            volumes=volume,
            remove=True,
        )

    osrm_backend(f"osrm-extract -p /opt/foot.lua {source}")
    osrm_backend(f"osrm-partition /data/{MAP_NAME}.osrm")
    osrm_backend(f"osrm-customize /data/{MAP_NAME}.osrm")


def start_osrm():
    global osrm_container

    if osrm_container is not None:
        return

    prepare_osrm()
    print(f"Starting osrm-routed on port {OSRM_PORT}")

    osrm_container = docker.from_env().containers.run(
        image=OSRM_IMAGE,
        command=f"osrm-routed --algorithm mld /data/{MAP_NAME}.osrm",
        volumes={str(DATA / "osrm"): {"bind": "/data", "mode": "ro"}},
        ports={"5000/tcp": OSRM_PORT},
        detach=True,
        remove=True,
    )

    atexit.register(stop_osrm)
    time.sleep(1)


def stop_osrm():
    global osrm_container

    if osrm_container is not None:
        print("Stopping osrm-routed")
        osrm_container.stop()
        osrm_container = None


def osrm_table(coords, sources=None):
    srcs = f"&sources={sources}" if sources else ""
    url = f"http://localhost:{OSRM_PORT}/table/v1/foot/{coords}?annotations=distance{srcs}"

    while True:
        try:
            response = requests.get(url).text

            if response.find('"code":"Ok"') != -1:
                return response

        except Exception as e:
            response = str(e)

        print(f"OSRM error: {response}")
        time.sleep(3)


def make_transit_db():
    if TRANSIT_DB.exists():
        return

    TMP_DB.parent.mkdir(exist_ok=True)
    TMP_DB.unlink(missing_ok=True)

    with duckdb.connect(TMP_DB) as db:
        print("Initializing transit DB")
        db.sql(read(SQL / "transit" / "init.sql"))

        get_gtfs()
        print("Importing GTFS")
        with working_dir(ROOT):
            db.sql(read(SQL / "transit" / "import-gtfs.sql"))

        calc_stop_walks(db)

        print("Generating connections")
        db.sql(read(SQL / "transit" / "generate-connections.sql"))

        db.sql("analyze")

    TMP_DB.rename(TRANSIT_DB)


def calc_stop_walks(db):
    print("Calculating walking distances between stops")
    start_osrm()
    tp = threadpool()

    input = db.sql(read(SQL / "transit" / "stop-walk" / "init.sql")).fetchnumpy()
    futures = [tp.submit(osrm_table, c, "0") for c in input["coords"]]
    insert = read(SQL / "transit" / "stop-walk" / "insert.sql")

    for from_stop, to_stops, future in zip(input["from_stop"], input["to_stops"], futures):
        from_stop = np.array([from_stop])
        to_stop = pd.DataFrame({'i': np.arange(1, len(to_stops)+1), 'id': to_stops})
        osrm_response = np.array([future.result()])
        db.sql(insert)


def get_dataset_metadata():
    make_transit_db()

    with duckdb.connect(TRANSIT_DB) as db:
        return db.sql(read(SQL / "transit" / "get-dataset-metadata.sql")).fetchone()[0]


def make_walks_db(path, size):
    meta = get_dataset_metadata()

    with duckdb.connect(path) as db:
        db.sql(read(SQL / "walks" / "init.sql"))
        cur_size = db.table("walk").count("*").fetchone()[0]

        if cur_size >= size:
            return

        print(f"Generating {path.relative_to(Path.cwd())} ({size} rows)")
        start_osrm()
        tp = threadpool()

        batches = math.ceil((size-cur_size)/OSRM_TABLE_OUTPUT)
        futures = [tp.submit(gen_walks_batch, meta) for _ in range(0, batches)]
        insert = read(SQL / "walks" / "insert.sql")

        for f in futures:
            # SQL inputs
            coords, osrm_response = f.result()
            db.sql(insert)


def gen_walks_batch(meta):
    n = OSRM_TABLE_BATCH
    c = meta["centroid"]
    d = meta["max_dev"]

    lat = np.random.normal(c["lat"], d["lat"] / 3, n).astype('float32')
    lon = np.random.normal(c["lon"], d["lon"] / 3, n).astype('float32')
    coords_str = ";".join(f"{lon},{lat}" for lat, lon in zip(lat, lon))

    osrm_response = np.array([osrm_table(coords_str)])
    coords = pd.DataFrame({'i': np.arange(1, n+1), 'lat': lat, 'lon': lon})
    return (coords, osrm_response)


def read(path):
    with open(path, "r") as file:
        return file.read()


@contextlib.contextmanager
def working_dir(path):
    current = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(current)


def threadpool() -> ThreadPoolExecutor:
    global threadpool_handle

    if threadpool_handle is None:
        threadpool_handle = ThreadPoolExecutor(max_workers=os.cpu_count())
        atexit.register(shutdown_threadpool)
    
    return threadpool_handle


def shutdown_threadpool():
    global threadpool_handle

    if threadpool_handle is not None:
        threadpool_handle.shutdown()


if __name__ == "__main__":
    make_transit_db()
