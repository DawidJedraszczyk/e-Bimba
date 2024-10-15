import duckdb
import functools
from pathlib import Path
import pyarrow

from lib.common import *


class TransitDb:
  def __init__(self, path: Path):
    self.db = duckdb.connect(path)
    self.sql = Path(__file__).parent / ".." / "sql" / "transit"
    self.db.sql("install spatial; load spatial")

  def __enter__(self):
    return self

  def __exit__(self):
    self.db.close()

  def nearest_stops(self, lat: float, lon: float) -> pyarrow.StructArray:
    return arrow(self.db.sql(
      self.load("get-nearest-stops"),
      params={"lat":lat, "lon":lon},
    ))

  @functools.cache
  def load(self, name):
    with open(self.sql / f"{name}.sql", "r") as file:
        return file.read()


def arrow(rel) -> pyarrow.StructArray:
  return rel.arrow().to_struct_array().combine_chunks()
