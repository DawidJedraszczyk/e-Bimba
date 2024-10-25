from dataclasses import dataclass
import datetime
import duckdb
import functools
from pathlib import Path
import pyarrow
from typing import TypedDict, cast

import lib.connections
import lib.params


@dataclass
class Result:
  rel: duckdb.DuckDBPyRelation

  def scalar(self):
    return self.rel.fetchone()[0]

  def arrow(self) -> pyarrow.StructArray:
    return self.rel.arrow().to_struct_array().combine_chunks() # type: ignore


class Services(TypedDict):
  yesterday: list[int]
  today: list[int]
  tomorrow: list[int]


class TransitDb:
  db: duckdb.DuckDBPyConnection
  scripts: Path

  def __init__(self, path: Path):
    self.db = duckdb.connect(path)
    self.scripts = Path(__file__).parent / ".." / "sql" / "transit"
    self.db.sql("install spatial; load spatial")

    for k, v in lib.params.__dict__.items():
      if not k.startswith("_"):
        self.db.sql(f"set variable {k} = {v}")

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.db.close()

  def get_services(self, date: datetime.date) -> Services:
    return self.sql("select get_service_lists(?)", (date,)).scalar()

  def nearest_stops(self, lat: float, lon: float) -> pyarrow.StructArray:
    return self.script("get-nearest-stops", {"lat":lat, "lon":lon}).arrow()

  def get_connections(self) -> lib.connections.Connections:
    cs = self.sql("select to_stops from connections order by from_stop").arrow().field(0)
    return lib.connections.from_arrow(cast(pyarrow.ListArray, cs))

  def sql(self, query: str, params=None, views={}) -> Result:
    for k, v in views.items():
      self.db.register(k, v)

    r = Result(self.db.sql(query, params=params))

    for k in views.keys():
      self.db.unregister(k)

    return r

  def script(self, script_name: str, params=None, views={}) -> Result:
    return self.sql(self.load(script_name), params, views)

  @functools.cache
  def load(self, name: str):
    path = self.scripts
    parts = name.split("/")
    parts[-1] += ".sql"

    for part in parts:
      path = path / part

    with open(path, "r") as file:
        return file.read()
