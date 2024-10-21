from dataclasses import dataclass
import datetime
import duckdb
import functools
from pathlib import Path
import pyarrow
from typing import TypedDict, cast


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

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.db.close()

  def get_services(self, date: datetime.date) -> Services:
    return self.sql("select get_service_lists(?)", (date,)).scalar()

  def nearest_stops(self, lat: float, lon: float) -> pyarrow.StructArray:
    return self.script("get-nearest-stops", {"lat":lat, "lon":lon}).arrow()

  def get_connections(self) -> pyarrow.StructArray:
    return self.sql("select * from connections").arrow()

  def sql(self, query: str, params=None) -> Result:
    return Result(self.db.sql(query, params=params))

  def script(self, script_name: str, params=None) -> Result:
    return Result(self.db.sql(self.load(script_name), params=params))

  @functools.cache
  def load(self, name: str):
    with open(self.scripts / f"{name}.sql", "r") as file:
        return file.read()
