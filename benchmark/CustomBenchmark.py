import csv
import os

from benchmark.BenchmarkStrategy import BenchmarkStrategy
from benchmark.routes_generating.custom_routes import get_custom_sample_routes
from algorithm_parts.utils import seconds_to_time

class CustomBenchmark(BenchmarkStrategy):
    def __init__(self):
        BenchmarkStrategy.__init__(self)
        self.benchmark_type = 'custom_benchmark'
        self.sample_routes = get_custom_sample_routes()

    def print_results_to_csv(self):
        filename = self.get_csv_filename()
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Time searching',
                            'Start name',
                            'Destination Name',
                            'Start Time',
                            'Day of week',
                            #'found route',
                            'jak dojade route',
                            'google route',
                            'found route duration',
                            'jak dojade duration',
                            'google route duration'
                            ])
            for i, route in enumerate(self.sample_routes):
                writer.writerow([
                    round(self.total_times[i], 3),
                    route.start_name, 
                    route.destination_name, 
                    route.start_time,
                    route.week_day,
                    #plans_to_string(planners[i].found_plans), TODO: look at the comment in BenchmarkStrategy
                    str(route.jakdojade_plan),
                    str(route.google_plan),
                    self.compute_travel_duration(
                        route.start_time,
                        seconds_to_time(self.planners[i].found_plans[0].time_at_destination)),
                    self.compute_travel_duration(
                        route.start_time, 
                        route.jakdojade_plan.arrival_time),
                    self.compute_travel_duration(route.start_time, route.google_plan.arrival_time)
                    ])