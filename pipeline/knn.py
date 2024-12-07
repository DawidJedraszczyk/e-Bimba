#!/usr/bin/env python3

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parents[1] / "ebus"))
sys.path.append(str(Path(__file__).parent))

from common import *

if len(sys.argv) == 1:
  print(f"Usage: {sys.argv[0]} CITY")
  sys.exit()
else:
  city_name = " ".join(sys.argv[1:])
  city = get_city(city_name)

  if city is None:
    print(f"Unknown city '{city_name}'")
    sys.exit()

from transit.knndb import *


knndb = KnnDb(DATA_CITIES / f"{city['id']}-knn.db", write=True)
knndb.set_variable("SRC", str(TMP_CITIES / city['id'] / "dataset.parquet"))
knndb.script("init")
