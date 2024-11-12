#!/usr/bin/env python3

from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
sys.path.extend([
  str(ROOT),
  str(ROOT / "app"),
  str(ROOT / "app" / "apps" / "route_search" / "modules"),
])

from benchmark.components.SampleRoute import SampleRoute
from benchmark.BenchmarkStrategy import BenchmarkStrategy
from benchmark.CustomBenchmark import CustomBenchmark
from benchmark.SmallAutoBenchmark import SmallAutoBenchmark
from benchmark.FullAutoBenchmark import FullAutoBenchmark

# Warm up numba
b = BenchmarkStrategy()
b.sample_routes = [SampleRoute("Smochowice - przejazd kolejowy", "Głuszyna", '7:30:00', date='2024-09-05')]
b.run()
b.print_found_routes()

b = CustomBenchmark()
b.run()
b.print_results_to_csv()

b = SmallAutoBenchmark()
b.run()
b.print_results_to_csv()
