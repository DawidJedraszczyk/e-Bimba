#!/usr/bin/env python3

import numpy as np
from pathlib import Path
import pyarrow.parquet as pq
from sklearn.neighbors import KNeighborsRegressor
import pickle
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


N = 5

dataset_path = TMP_CITIES / city["id"] / "dataset.parquet"
dataset = pq.read_table(dataset_path)

X = np.stack(
  [
    dataset["from_x"],
    dataset["from_y"],
    dataset["to_x"],
    dataset["to_y"],
    dataset["day_type"],
    dataset["start"],
  ],
  axis=-1,
  dtype="float32",
)

Y = dataset["time"].to_numpy()

knnr = KNeighborsRegressor(N, algorithm="kd_tree")
knnr.fit(X, Y)


with (DATA_CITIES / f"{city['id']}-knn.pkl").open("wb") as file:
  pickle.dump(knnr, file)
