import datetime
from functools import lru_cache
import os
from pathlib import Path
from time import time

from transit.data.misc import Metadata, Services
from transit.data.routes import Routes
from transit.data.shapes import Shapes
from transit.data.stops import Stops
from transit.data.trips import Trips
from transit.osrm import OsrmClient
from transit.prospector import Prospector
from transit.transitdb import TransitDb
from .utils import custom_print


class Data:
    tdb: TransitDb
    md: Metadata
    routes: Routes
    shapes: Shapes
    stops: Stops
    trips: Trips
    prospector: Prospector

    _instances = dict()

    @staticmethod
    def instance(db_path: Path):
        key = db_path.absolute()
        ins = Data._instances.get(key, None)

        if ins is None:
            t0 = time()
            ins = Data(db_path)
            Data._instances[key] = ins
            custom_print(f'(Data - {time() - t0:.4f}s)', 'SETUP_TIMES')

        return ins

    def __init__(self, db_path: Path):
        self.tdb = TransitDb(db_path)
        self.md = self.tdb.get_metadata()
        self.routes = self.tdb.get_routes()
        self.shapes = self.tdb.get_shapes()
        self.stops = self.tdb.get_stops()
        self.trips = self.tdb.get_trips()

        var = f"OSRM_URL_{self.md.region}"
        osrm_url = os.environ.get(var, None)

        if osrm_url is None:
            raise Exception(f"Missing env var {var}")

        self.prospector = Prospector(
            self.tdb,
            OsrmClient(osrm_url),
            self.md,
            self.stops,
        )

    @lru_cache
    def services_around(self, date: datetime.date) -> Services:
        return self.tdb.get_services(date)
