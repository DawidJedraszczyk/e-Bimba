import datetime
from functools import lru_cache
from pathlib import Path
from time import time

from bimba.data.common import Services
from bimba.data.routes import Routes
from bimba.data.shapes import Shapes
from bimba.data.stops import Stops
from bimba.data.trips import Trips
from bimba.transitdb import TransitDb
from .utils import custom_print

try:
    from django.conf import settings
    _DB_PATH = Path(settings.BASE_DIR) / "transit.db"
except:
    _DB_PATH = Path(__file__).parents[5] / "data" / "main" / "transit.db"


class Data:
    _instance = None

    @staticmethod
    def instance():
        if Data._instance is None:
            t0 = time()
            Data._instance = Data()
            custom_print(f'(Data - {time() - t0:.4f}s)', 'SETUP_TIMES')

        return Data._instance

    def __init__(self):
        self.tdb = TransitDb(_DB_PATH)
        self.routes = self.tdb.get_routes()
        self.shapes = self.tdb.get_shapes()
        self.stops = self.tdb.get_stops()
        self.trips = self.tdb.get_trips()

    @lru_cache
    def services_around(self, date: datetime.date) -> Services:
        return self.tdb.get_services(date)
