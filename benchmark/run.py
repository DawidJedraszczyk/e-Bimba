#!/usr/bin/env python3

import os
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.extend([
  str(ROOT / "benchmark"),
  str(ROOT / "ebus"),
  str(ROOT / "pipeline"),
])

from algorithm.data import *
from components.SampleRoute import SampleRoute
from strategies.BenchmarkStrategy import BenchmarkStrategy
from strategies.CustomBenchmark import CustomBenchmark
from strategies.SmallAutoBenchmark import SmallAutoBenchmark
from strategies.FullAutoBenchmark import FullAutoBenchmark
from common import OSRM_PORT, start_osrm

with start_osrm("pl_wielkopolskie"):
  os.environ["OSRM_URL_pl_wielkopolskie"] = f"http://localhost:{OSRM_PORT}"
  data = Data.instance(ROOT / "data" / "cities" / "poz-w.db")

  # Warm up numba
  b = BenchmarkStrategy(data)
  b.sample_routes = [SampleRoute("Smochowice - przejazd kolejowy", "Głuszyna", '7:30:00', date='2024-09-05')]
  b.run()
  b.print_found_routes()

  b = CustomBenchmark(data)
  b.run()
  b.print_results_to_csv()

  b = SmallAutoBenchmark(data)
  b.run()
  b.print_results_to_csv()
