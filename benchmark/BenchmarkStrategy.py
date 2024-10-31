from abc import abstractmethod
from datetime import datetime
from time import time
import os

from algorithm_parts.utils import time_to_seconds, seconds_to_time, custom_print, plans_to_string
from algorithm_parts.AStarPlanner import AStarPlanner

class BenchmarkStrategy():
    benchmark_type = None
    alternative_routes = 3
    planner_metric = 'manhattan' # at the end when we will use neural network this will be removed or serve other purpose
    total_times = []
    planners = []
    sample_routes = None

    def __init__(self):
        pass

    def run(self):
        self.total_times = []
        self.planners = []
        for route in self.sample_routes:
            start = route.start_cords
            destination = route.destination_cords
            start_time = time_to_seconds(route.start_time)
            start_date = route.date
            weekday = route.week_day

            planner = AStarPlanner(start_time,start,destination,self.planner_metric,start_date)            
            total_time = 0

            custom_print(
                f'Searching for route from: {route.start_name} {start} '
                f'to: {route.destination_name} {destination} '
                f'at time: {route.start_time} {route.date} '
                f'({weekday})', 'BENCHMARK')
            
            for _ in range(self.alternative_routes):
                t0 = time()
                _ = planner.find_next_plan()
                custom_print(f'(AStarPlannerStraight.find_next_plan = {time()-t0:.4f}s)', 'BENCHMARK')
                total_time += time()-t0

            self.total_times.append(total_time)
            self.planners.append(planner)

    def print_found_routes(self):
        for i, route in enumerate(self.sample_routes):
            print('##################################################')
            print('Route from: ', route.start_name, 'to: ', route.destination_name, 'at time: ', route.start_time, ' on: ', route.week_day)
            print('##################################################')
            print(plans_to_string(self.planners[i].found_plans))
            route.print_comparison_plans()

    @abstractmethod
    def print_results_to_csv(self):
        pass

    #private methods:
    def compute_travel_duration(self, start_time, end_time):
        start_time_in_seconds = time_to_seconds(start_time)
        end_time_in_seconds = time_to_seconds(end_time)
        if end_time_in_seconds < start_time_in_seconds:
            end_time_in_seconds += time_to_seconds("24:00:00")
        duration = end_time_in_seconds - start_time_in_seconds
        return seconds_to_time(duration)
    
    def get_csv_filename(self):
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        directory = f"benchmark_results/{current_time}"
        os.makedirs(directory, exist_ok=True)
        filename = os.path.join(directory, f"{self.benchmark_type}_results{current_time}.csv")
        return filename
    