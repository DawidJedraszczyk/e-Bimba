import numpy as np
from pathlib import Path

from .db import Db


class KnnDb(Db):
  def __init__(self, path: Path, write=False):
    scripts = Path(__file__).parent / "knndb-sql"
    super().__init__(path, scripts, write)
    self.sql("install vss; load vss")


  def search(self, inputs: np.ndarray, n=1) -> np.ndarray:
    params = {"inputs": inputs, "n": n}
    return self.script("search", params).np()["output"]
