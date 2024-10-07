#!/usr/bin/env python3

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

    with open(path, "wb") as file:
        res = requests.get(url)
        file.write(res.content)


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

    with duckdb.connect(db_tmp) as db:

        def scalar(query):
            return db.sql(query).fetchone()[0]

        try:
            if not scalar("select 'connection' in (show tables)"):
                print("Creating schema")
                db.sql(read(sql / "01-schema.sql"))

            if scalar("select count(*) from agency") == 0:
                print("Importing GTFS")
                with working_dir(root):
                    db.sql(read(sql / "02-import.sql"))
        except:
            db.close()
            db_tmp.unlink(missing_ok=True)
            raise

        if scalar("select count(*) from connection") == 0:
            print("Generating connections")
            db.sql(read(sql / "03-generate.sql"))

        if scalar("select count(*) from walk") == 0:
            print("Calculating walking distances")
            with run_osrm():
                calc_walking(db)

        db.sql(read(sql / "04-index.sql"))

    db_tmp.rename(db_file)


def calc_walking(db: duckdb.DuckDBPyConnection):
    # TODO
    pass


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
