import csv
import os

from benchmark.BenchmarkStrategy import BenchmarkStrategy
from benchmark.routes_generating.automatic_routes import get_small_instance_automatic_sample_routes
from algorithm_parts.utils import seconds_to_time, plans_to_string

class SmallAutoBenchmark(BenchmarkStrategy):
    def __init__(self):
        BenchmarkStrategy.__init__(self)
        self.benchmark_type = 'small_automatic_benchmark'
        self.sample_routes = get_small_instance_automatic_sample_routes()

    def print_results_to_csv(self):
        filename = self.get_csv_filename()
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Time searching',
                            'Start name',
                            'Destination Name',
                            'Start Time',
                            'Day of week',
                            'found route',
                            'found route duration',
                            ])
            for i, route in enumerate(self.sample_routes):
                writer.writerow([
                    round(self.total_times[i], 3),
                    route.start_name, 
                    route.destination_name, 
                    route.start_time,
                    route.week_day,
                    plans_to_string(self.planners[i].found_plans),
                    self.compute_travel_duration(
                        route.start_time,
                        seconds_to_time(self.planners[i].found_plans[0].time_at_destination)) if self.planners[i].found_plans else 'NA',
                    ])
