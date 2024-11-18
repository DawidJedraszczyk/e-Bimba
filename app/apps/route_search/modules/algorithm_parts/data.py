import datetime
from functools import lru_cache
from pathlib import Path
from time import time

from bimba.data.misc import Services
from bimba.data.routes import Routes
from bimba.data.shapes import Shapes
from bimba.data.stops import Stops
from bimba.data.trips import Trips
from bimba.transitdb import TransitDb
from .utils import custom_print


class Data:
    _instances = dict()

    @staticmethod
    def instance(db_path):
        if db_path not in Data._instances:
            t0 = time()
            Data._instances[db_path] = Data(db_path)
            custom_print(f'(Data - {time() - t0:.4f}s)', 'SETUP_TIMES')

        return Data._instances[db_path]

    def __init__(self, db_path):
        self.tdb = TransitDb(db_path)
        self.routes = self.tdb.get_routes()
        self.shapes = self.tdb.get_shapes()
        self.stops = self.tdb.get_stops()
        self.trips = self.tdb.get_trips()

    @lru_cache
    def services_around(self, date: datetime.date) -> Services:
        return self.tdb.get_services(date)
