#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor
import contextlib
import docker
import duckdb
import os
from pathlib import Path
import requests
import zipfile

root = Path(__file__).parent
data = root / "data"
sql = root / "sql"
db_file = data / "transit.db"
db_tmp = data / "tmp.db"
gtfs_zip = data / "gtfs.zip"
gtfs_dir = data / "gtfs"
osrm_folder = data / "osrm"
map_name = "map"
osm_file = osrm_folder / f"{map_name}.osm.pbf"

gtfs_url = "https://www.ztm.poznan.pl/pl/dla-deweloperow/getGTFSFile"
osm_url = "http://download.geofabrik.de/europe/poland/wielkopolskie-latest.osm.pbf"

osrm_image = "ghcr.io/project-osrm/osrm-backend"
osrm_port = 53909


def download_if_missing(url, path):
    if path.exists():
        return

    path.parent.mkdir(exist_ok=True)
    print(f"Downloading '{url}' to '{path.relative_to(Path.cwd())}'")
    content = requests.get(url).content

    with open(path, "wb") as file:
        file.write(content)


def get_gtfs():
    if gtfs_dir.exists():
        return

    download_if_missing(gtfs_url, gtfs_zip)

    with zipfile.ZipFile(gtfs_zip, "r") as zip:
        zip.extractall(gtfs_dir)


def prepare_osrm(dc: docker.DockerClient):
    if (osrm_folder / f"{map_name}.osrm.fileIndex").exists():
        return

    download_if_missing(osm_url, osm_file)

    volume = {str(data / "osrm"): {"bind": "/data", "mode": "rw"}}
    source = f"/data/{osm_file.relative_to(osrm_folder)}"

    def osrm_backend(cmd):
        print(f"Running '{cmd}' in OSRM containter")

        dc.containers.run(
            image=osrm_image,
            command=cmd,
            volumes=volume,
            remove=True,
        )

    osrm_backend(f"osrm-extract -p /opt/foot.lua {source}")
    osrm_backend(f"osrm-partition /data/{map_name}.osrm")
    osrm_backend(f"osrm-customize /data/{map_name}.osrm")


@contextlib.contextmanager
def run_osrm():
    dc = docker.from_env()
    prepare_osrm(dc)

    print("Starting osrm-routed")

    container = dc.containers.run(
        image=osrm_image,
        command=f"osrm-routed --algorithm mld /data/{map_name}.osrm",
        volumes={str(data / "osrm"): {"bind": "/data", "mode": "ro"}},
        ports={"5000/tcp": osrm_port},
        detach=True,
        remove=True,
    )

    try:
        yield
    finally:
        container.stop()


def gen_db():
    if db_file.exists():
        return

    db_tmp.parent.mkdir(exist_ok=True)

    with duckdb.connect(db_tmp) as db:

        def scalar(query):
            return db.sql(query).fetchone()[0]

        try:
            if not scalar("select 'connection' in (show tables)"):
                print("Creating tables")
                db.sql(read(sql / "create-tables.sql"))

            if scalar("select count(*) from agency") == 0:
                get_gtfs()
                print("Importing GTFS")
                with working_dir(root):
                    db.sql(read(sql / "import-gtfs.sql"))
        except:
            db.close()
            db_tmp.unlink(missing_ok=True)
            raise

        if scalar("select count(*) from connection") == 0:
            print("Generating connections")
            db.sql(read(sql / "generate-connections.sql"))

        if scalar("select count(*) from walk") == 0:
            print("Calculating walking distances")
            with run_osrm():
                walk_calc(db)

        db.sql(read(sql / "index.sql"))

    db_tmp.rename(db_file)


def walk_calc(db: duckdb.DuckDBPyConnection):
    walk_calc_init(db)

    # Repeating in loop to handle intermittent OSRM failures
    while True:
        calcs = db.sql(
            "select id, from_stop, coords from walk_calc where distances is null"
        ).fetchall()

        if len(calcs) == 0:
            break

        executor = ThreadPoolExecutor(max_workers=os.cpu_count())

        for id, from_stop, coords in calcs:
            executor.submit(walk_calc_one, id, from_stop, coords, db.cursor())

        executor.shutdown(wait=True)

    db.sql(read(sql / "walk-calc-finish.sql"))


def walk_calc_one(id, from_stop, coords, db):
    query = f"""
      update walk_calc set distances = (
        select distances[1][2:] from read_json(
          'http://localhost:{osrm_port}/table/v1/foot/{coords}?sources=0&annotations=distance'
        )
      ) where id = {id}
    """

    print(f"Calculating walking distances from {from_stop}")
    db.sql(query)


def walk_calc_init(db: duckdb.DuckDBPyConnection):
    try:
        if db.sql("select count(*) from walk_calc").fetchone()[0] > 0:
            return
    except:
        pass

    print("Creating temp table walk_calc")
    db.sql(read(sql / "walk-calc-init.sql"))


def all():
    gen_db()


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


if __name__ == "__main__":
    all()
