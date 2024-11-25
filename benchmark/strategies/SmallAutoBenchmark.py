import csv
import os

from strategies.BenchmarkStrategy import BenchmarkStrategy
from routes_generating.automatic_routes import get_small_instance_automatic_sample_routes

class SmallAutoBenchmark(BenchmarkStrategy):
    def __init__(self, data):
        BenchmarkStrategy.__init__(self, data)
        self.benchmark_type = 'small_automatic_benchmark'
        self.sample_routes = get_small_instance_automatic_sample_routes()

    def print_results_to_csv(self):
        filename = self.get_csv_filename()
        with open(filename, mode='w', newline='') as file:
            common_metrics_csv_row_dict = self.get_common_metrics_csv_row_dict(self.sample_routes[0], 0, self.planners[0].metrics)
            fieldnames = common_metrics_csv_row_dict.keys()
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for route_index, route in enumerate(self.sample_routes):
                planner = self.planners[route_index]
                writer.writerow(self.get_common_metrics_csv_row_dict(route, route_index, planner.metrics))
