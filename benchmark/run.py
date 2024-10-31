#!/usr/bin/env python3

from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
sys.path.extend([
  str(ROOT),
  str(ROOT / "app"),
  str(ROOT / "app" / "apps" / "route_search" / "modules"),
])

from benchmark.CustomBenchmark import CustomBenchmark
from benchmark.SmallAutoBenchmark import SmallAutoBenchmark
from benchmark.FullAutoBenchmark import FullAutoBenchmark

b = CustomBenchmark()
b.run()
b.print_results_to_csv()

b = FullAutoBenchmark()
b.run()
b.print_results_to_csv()
