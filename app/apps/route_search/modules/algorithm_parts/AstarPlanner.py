import heapq
from time import time
from haversine import haversine, Unit
from itertools import combinations

try:
    from django.templatetags.static import static
except:
    pass

from .utils import get_lat_lon_sets, get_closest_shape_point, get_next_day, time_to_seconds, get_previous_day, manhattan_distance, custom_print, seconds_to_time
from .Plan import Plan
from .PlanTrip import PlanTrip
from .DataLoaderSingleton import initialized_dataloader_singleton
from ebus.algorithm_settings import WALKING_SETTINGS, HEURISTIC_SETTINGS, PRINTING_SETTINGS


class AStarPlanner():
    def __init__(self, start_time, START, DESTINATION, distance_metric, current_date,
                 waiting_time_constant=time_to_seconds('00:03:00')):
        data_loader = initialized_dataloader_singleton
        self.stops = data_loader.get_stops()
        self.stops_df = data_loader.get_stops_df()
        self.trips = data_loader.get_trips()
        self.trips_df = data_loader.get_trips_df()
        self.shapes_df = data_loader.get_shapes_df()
        self.start_time = start_time
        self.START = START
        self.DESTINATION = DESTINATION
        self.distance_metric = distance_metric
        self.waiting_time_constant = waiting_time_constant
        self.start_walking_times = self.__get_start_walking_times()
        self.destination_walking_times = self.__get_destination_walking_times()
        self.heuristic_times = self.__get_destination_heurisitc_time()
        self.start_within_walking = self.__get_start_within_walking()
        self.plans_queue = []
        for stop_id in self.start_within_walking.keys():
            plan = Plan(
                self.start_walking_times,
                self.destination_walking_times,
                self.heuristic_times,
                self.start_time,
                current_date,
                starting_stop_id=stop_id)
            plan.compute_heuristic_time_at_destination()
            heapq.heappush(self.plans_queue, plan)
        self.found_plans = list()
        self.iterations = 0
        self.metrics = {
            'iterations': 0, #i
            'unique_stops_visited': 0, #i
            'plans_queue_max_size': 0, #i
            'all_stops_retrieved_total': 0, #i sum, over all iterations, of all the stops that were connected to the current stop, there may be repetitions
            'expansions_total' : 0, #i
            'walking_expansions_total': 0, #i
            'trasnit_expansions_total': 0, #i
            'get_next_trips_time_total': 0,
            'plan_compute_heurstic_time_total': 0,
            'plan_compute_actual_time_total': 0,
        }

    # returns negative value if fastest_way is faster than alternative_way
    def __compute_trips_arrival_time_difference(self, fastest_way, alternative_way_arrival_time_s,
                                                alterntaive_way_date):
        if fastest_way.date == alterntaive_way_date:
            difference = fastest_way.arrival_time - alternative_way_arrival_time_s
        elif fastest_way.date == get_previous_day(alterntaive_way_date):
            difference = fastest_way.arrival_time - (alternative_way_arrival_time_s + time_to_seconds('24:00:00'))
        elif fastest_way.date == get_next_day(alterntaive_way_date):
            difference = fastest_way.arrival_time - (alternative_way_arrival_time_s - time_to_seconds('24:00:00'))
        else:
            raise ValueError(f"Dates of arrival are too far apart: {fastest_way.date} and {alterntaive_way_date}")
        return difference

    # TODO: This methods that will be used every time new route is searched,
    # and thus should be optimized for time perfomance
    # Also they must be made more accurate in the future, possibly with help of OSRM

    def __get_start_walking_times(self):
        t0 = time()
        if self.distance_metric == 'straight':
            start_walking_times = {
                stop.stop_id: haversine(
                    (stop.stop_lat, stop.stop_lon), self.START,
                    unit=Unit.METERS
                ) / WALKING_SETTINGS['PACE']
                for stop in self.stops.values()
            }
        elif self.distance_metric == 'manhattan':
            start_walking_times = {
                stop.stop_id: manhattan_distance(
                    stop.stop_lat, stop.stop_lon,
                    self.START[0], self.START[1]
                ) / WALKING_SETTINGS['PACE']
                for stop in self.stops.values()
            }
        else:
            raise ValueError(f'Unknown distance metric: {self.distance_metric}')
        custom_print(f'(start_walking_times_straight - {time() - t0:.4f}s)', 'ALGORITHM_PREPROCESSING_TIMES')
        return start_walking_times

    def __get_start_within_walking(self):
        t0 = time()
        # TODO - may need to specify incremental increase in case no route found?
        #   or similar "at least X"? or somehow "without explicit"?
        start_within_walking = {
            stop_id: walking_time
            for stop_id, walking_time in self.start_walking_times.items()
            if walking_time <= WALKING_SETTINGS['TIME_WITHIN_WALKING']
        }
        custom_print(f'(start_within_walking - {time() - t0:.4f}s)', 'ALGORITHM_PREPROCESSING_TIMES')
        return start_within_walking

    def __get_destination_walking_times(self):
        t0 = time()
        if self.distance_metric == 'straight':
            destination_walking_times = {
                stop.stop_id: haversine(
                    (stop.stop_lat, stop.stop_lon), self.DESTINATION,
                    unit=Unit.METERS
                ) / WALKING_SETTINGS['PACE']
                for stop in self.stops.values()
            }
        elif self.distance_metric == 'manhattan':
            destination_walking_times = {
                stop.stop_id: manhattan_distance(
                    stop.stop_lat, stop.stop_lon,
                    self.DESTINATION[0], self.DESTINATION[1]
                ) / WALKING_SETTINGS['PACE']
                for stop in self.stops.values()
            }
        else:
            raise ValueError(f'Unknown distance metric: {self.distance_metric}')
        custom_print(f'(destination_walking_times_straight - {time() - t0:.4f}s)', 'ALGORITHM_PREPROCESSING_TIMES')
        return destination_walking_times

    def __get_destination_heurisitc_time(self):
        # This may be overestimating (especially in Manhattan) -> potential problems
        #   BUT note that this may work in practice anyways
        # heuristic = time with tram avg speed to dest + assumed walking time constant
        t0 = time()
        if self.distance_metric == 'straight':
            heuristic_times = {
                stop.stop_id: haversine(
                    (stop.stop_lat, stop.stop_lon), self.DESTINATION,
                    unit=Unit.METERS
                ) / WALKING_SETTINGS['PACE'] + HEURISTIC_SETTINGS['ALWAYS_WALKING_TIME_CONSTANT']
                for stop in self.stops.values()
            }
        elif self.distance_metric == 'manhattan':
            heuristic_times = {
                stop.stop_id: manhattan_distance(
                    stop.stop_lat, stop.stop_lon,
                    self.DESTINATION[0], self.DESTINATION[1]
                ) / HEURISTIC_SETTINGS['MAX_SPEED'] + HEURISTIC_SETTINGS['ALWAYS_WALKING_TIME_CONSTANT']
                for stop in self.stops.values()
            }
        else:
            raise ValueError(f'Unknown distance metric: {self.distance_metric}')
        custom_print(f'(destination_heuristic_times - {time() - t0:.4f}s)', 'ALGORITHM_PREPROCESSING_TIMES')
        return heuristic_times

    # Mere algorithm
    def find_next_plan(self):
        visited_stops = set()
        while len(self.plans_queue) != 0:
            self.iterations += 1

            if not self.plans_queue:
                raise Exception('no more plans')

            # remove fastest known plan yet from queue
            t = time()
            plan_accepted = False
            while not plan_accepted:
                fastest_known_plan = heapq.heappop(self.plans_queue)
                # if this it True, it means that:
                # - heuristic doesn't point at anything potentially better
                # - among terminal plans in the queue, this is the fastest
                if fastest_known_plan.is_terminal:
                    self.found_plans.append(fastest_known_plan)
                    custom_print(self.iterations, 'ALGORITHM_ITERATIONS')
                    self.metrics['iterations'] = self.iterations
                    self.metrics['unique_stops_visited'] = len(visited_stops)
                    return fastest_known_plan
                if len(fastest_known_plan.plan_trips) == 0:
                    plan_accepted = True
                    continue
                last_stop_id = fastest_known_plan.plan_trips[-1].leave_at_stop_id
                # WARNING - this should to be tested, Most certainly it is wrong for neural network heuristic
                # there may be more effecitive way to the node.
                # The plan should be rejected, only if if it gets to visited stop in longer time
                if last_stop_id not in visited_stops:
                    plan_accepted = True
                    visited_stops.add(last_stop_id)

            # make this plan potential subject for terminal
            # (it was the best option so far and if remains so after we consider its
            # actual walking distance directly => there is no better plan)
            fastest_known_plan.set_as_terminal()
            # push it back to the queue
            heapq.heappush(self.plans_queue, fastest_known_plan)

            # print(f'visited {fastest_known_plan.current_stop_id}, on {seconds_to_time(fastest_known_plan.current_time)} - time at destination: {seconds_to_time(fastest_known_plan.heuristic_time_at_destination)}, [{fastest_known_plan.arrival_date}]')

            # try extending queue with fastest ways to all reachable stops
            # from stop we're currently at after following fastest known plan yet
            current_stop = self.stops[fastest_known_plan.current_stop_id]
            fastest_ways = dict()
            ## factor in trips from this stop directly
            available_trips = current_stop.get_next_trips(
                start_time_s=fastest_known_plan.current_time + self.waiting_time_constant,
                date_str=fastest_known_plan.arrival_date)

            if available_trips:
                for trip_id, (stop_index_in_sequence, departure_time, trip_date) in available_trips.items():
                    if trip_id in fastest_known_plan.used_trips:
                        continue  # covered in other plans, would be duplication
                    trip = self.trips[trip_id]
                    for i in range(stop_index_in_sequence + 1, len(trip.stop_ids)):
                        stop_id, arrival_time = trip.stop_ids[i], trip.arrival_times_s[i]
                        if stop_id not in fastest_ways.keys() or self.__compute_trips_arrival_time_difference(
                                fastest_ways[stop_id],
                                arrival_time,
                                trip_date) > 0:
                            fastest_ways[stop_id] = PlanTrip(
                                trip_id=trip_id,
                                start_from_stop_id=current_stop.stop_id,
                                departure_time=departure_time,
                                leave_at_stop_id=stop_id,
                                arrival_time=arrival_time,
                                type='bus',  # TODO - change when distinction between buses and trams is implemented
                                date=trip_date
                            )
            else:
                custom_print('NO TRIPS AVAILABLE!', 'DEBUG')
            transit_trips_found = len(fastest_ways)

            ## factor in stops within walking distance
            for stop_id, walking_time in current_stop.stops_within_walking_straight.items():
                # TODO - get exact walking time
                if stop_id not in fastest_known_plan.used_stops:
                    time_at_stop = fastest_known_plan.current_time + walking_time + HEURISTIC_SETTINGS['ALWAYS_WALKING_TIME_CONSTANT']
                    if stop_id not in fastest_ways.keys() or self.__compute_trips_arrival_time_difference(
                            fastest_ways[stop_id],
                            time_at_stop,
                            fastest_known_plan.arrival_date) > 0:
                        fastest_ways[stop_id] = PlanTrip(
                            trip_id=None,
                            start_from_stop_id=current_stop.stop_id,
                            departure_time=fastest_known_plan.current_time,
                            leave_at_stop_id=stop_id,
                            arrival_time=time_at_stop,
                            type='WALK',
                            date=fastest_known_plan.arrival_date
                        )

            ## create extended plans and add them to the queue
            for stop_id, extending_plan_trip in fastest_ways.items():
                extended_plan = Plan(self.start_walking_times,
                                     self.destination_walking_times,
                                     self.heuristic_times,
                                     fastest_known_plan.start_time,
                                     extending_plan_trip.date,
                                     plan_trips=fastest_known_plan.plan_trips + [extending_plan_trip])
                extended_plan.compute_heuristic_time_at_destination()
                heapq.heappush(self.plans_queue, extended_plan)

            self.metrics['trasnit_expansions_total'] += transit_trips_found
            self.metrics['walking_expansions_total'] += (len(fastest_ways) - transit_trips_found)
            self.metrics['all_stops_retrieved_total'] += len(available_trips)
            self.metrics['all_stops_retrieved_total'] += len(current_stop.stops_within_walking_straight.items())
            self.metrics['expansions_total'] += len(fastest_ways)
            if len(self.plans_queue) > self.metrics['plans_queue_max_size']:
                self.metrics['plans_queue_max_size'] = len(self.plans_queue)

    def plans_to_html(self):
        response = {}

        for index, plan in enumerate(self.found_plans):
            communication = []
            start_time = None
            destination_time = seconds_to_time(plan.time_at_destination)

            for plan_trip in plan.plan_trips:
                if not plan_trip.type == 'WALK':
                    trip_from_df = self.trips_df.loc[plan_trip.trip_id]
                    if not start_time:
                        start_time = seconds_to_time(plan_trip.departure_time)

                    communication.append(trip_from_df['route_id'])

            communication_content = ''
            for travel_option in communication:
                communication_content += f'''<div style="padding: 5px; display: flex; flex-direction: column; justify-content: center; align-items: center;"><img style="height: 23px; width: 23px; margin-bottom: 5px;" src="{static('base_view/img/BUS.svg')}">{str(travel_option)}</div>'''

            prepared_solution = {
                'div': f'''<div style="display:none"></div>
                           <div id="{index}" class="solution" style="cursor: pointer; width: 99%; border: solid 1px white; padding: 20px 0px; border-radius: 5px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                               <div style="font-size: 25px; margin-left: 5px;">{start_time}</div>
                               <div style="display: flex;">{communication_content}</div>
                               <div style="font-size: 25px; margin-right: 5px;">{destination_time}</div>
                           </div>
                        '''
            }
            response[str(index)] = prepared_solution
        return response

    def prepare_coords(self, plan_num: int):
        response = {}

        plan = self.found_plans[plan_num]

        for index, plan_trip in enumerate(plan.plan_trips):
            if index == 0:
                start_stop = self.stops_df.loc[plan_trip.start_from_stop_id]
                response[0] = [self.START, (start_stop.stop_lat, start_stop.stop_lon)]

            if index == len(plan.plan_trips) - 1:
                goal_stop = self.stops_df.loc[plan_trip.leave_at_stop_id]
                response[len(plan.plan_trips) + 1] = [(goal_stop.stop_lat, goal_stop.stop_lon), self.DESTINATION]

            response[index + 1] = []
            sequence_numbers = []

            if plan_trip.trip_id:
                trip = self.trips[plan_trip.trip_id]
                shape_id = int(self.trips_df.loc[plan_trip.trip_id].shape_id)
                lat_lon_sets = get_lat_lon_sets(self.shapes_df, shape_id)
                trip_stops = [self.stops[stop_id] for stop_id in trip.stop_ids]

                for stop in trip_stops:
                    if stop.stop_id in (plan_trip.start_from_stop_id, plan_trip.leave_at_stop_id):
                        closest_point = get_closest_shape_point(stop.stop_lat, stop.stop_lon, lat_lon_sets)
                        closest_lat, closest_lon = closest_point

                        filtered_shape = self.shapes_df[
                            (self.shapes_df['shape_id'] == shape_id) &
                            (self.shapes_df['shape_pt_lat'] == closest_lat) &
                            (self.shapes_df['shape_pt_lon'] == closest_lon)
                            ]

                        if not filtered_shape.empty:
                            seq_num = int(filtered_shape['shape_pt_sequence'].iloc[0])
                            sequence_numbers.append(seq_num)

                if sequence_numbers:
                    min_seq_num = min(sequence_numbers)
                    max_seq_num = max(sequence_numbers)

                    matching_shapes = self.shapes_df[
                        (self.shapes_df['shape_id'] == shape_id) &
                        (self.shapes_df['shape_pt_sequence'] >= min_seq_num) &
                        (self.shapes_df['shape_pt_sequence'] <= max_seq_num)
                        ]

                    lat_lon_pairs = list(zip(matching_shapes['shape_pt_lat'], matching_shapes['shape_pt_lon']))
                    response[index + 1] = lat_lon_pairs

            else:
                start_stop = self.stops_df.loc[plan_trip.start_from_stop_id]
                goal_stop = self.stops_df.loc[plan_trip.leave_at_stop_id]

                response[index + 1] = [(start_stop.stop_lat, start_stop.stop_lon),
                                       (goal_stop.stop_lat, goal_stop.stop_lon)]

        return response

    def prepare_departure_details(self, plan_num: int, start_location: str, goal_location: str):
        response = {}

        plan = self.found_plans[plan_num]

        for index, plan_trip in enumerate(plan.plan_trips):
            if index == 0:
                start_stop = self.stops_df.loc[plan_trip.start_from_stop_id]
                response[0] = f'''<div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;"><img style="width: 25px;" src="{static('base_view/img/WALK.png')}"><span style="margin-left: 10px; text-align: left;">{start_location} -> {start_stop["stop_name"]}</span></div>'''

            if index == len(plan.plan_trips) - 1:
                goal_stop = self.stops_df.loc[plan_trip.leave_at_stop_id]
                response[
                    len(plan.plan_trips) + 1] = f'''<div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;"><img style="width: 25px;" src="{static('base_view/img/WALK.png')}"><span style="margin-left: 10px; text-align: left;"> {goal_stop["stop_name"]} -> {goal_location} </span></div>'''

            departure_time = seconds_to_time(plan_trip.departure_time)
            arrival_time = seconds_to_time(plan_trip.arrival_time)

            if plan_trip.trip_id:
                trip = self.trips_df.loc[plan_trip.trip_id]
                route = trip['route_id']
                direction = trip['trip_headsign']
                response[
                    index + 1] = f'''<div style="display: flex; width: 90%; flex-direction: column; justify-content: center; margin: 10px 0;"><div style="display:flex; align-items: center; margin: 10px 0;"><img src="{static('base_view/img/BUS.svg')}" alt="bus icon"/><span style="margin-left: 10px;">{route} - {direction} ({departure_time} - {arrival_time})</span></div><div class="stops" style="font-size: 14px; text-align: left;">'''

                trip_stops_ids = [stop_id for stop_id in self.trips[plan_trip.trip_id].stop_ids]
                in_our_trip_flag = False

                for stop_id in trip_stops_ids:
                    if stop_id == plan_trip.start_from_stop_id:
                        in_our_trip_flag = True

                    if in_our_trip_flag:
                        stop_df = self.stops_df.loc[stop_id]
                        stop_departure_time = "12:00"  # Update with actual logic for time if available
                        response[index + 1] += f'''{stop_departure_time} {stop_df['stop_name']}<br>'''

                    if stop_id == plan_trip.leave_at_stop_id:
                        in_our_trip_flag = False

            else:
                start_stop = self.stops_df.loc[plan_trip.start_from_stop_id]
                goal_stop = self.stops_df.loc[plan_trip.leave_at_stop_id]
                response[
                    index + 1] = f'''<div style="display: flex; width: 90%; justify-content: center; align-items: center; margin: 10px 0;"><img style="width: 25px;" src="{static('base_view/img/WALK.png')}"><span style="margin-left: 10px; text-align: left;"> {start_stop['stop_name']} -> {goal_stop['stop_name']}  ({departure_time} - {arrival_time})</span></div>'''

            response[index + 1] += "</div></div>"

        return response
