import datetime
import math
import numba as nb
import numpy as np
from typing import Callable, NamedTuple

from transit.data.misc import Point, DAY, INF_TIME
from transit.data.stops import Stops
from transit.prospector import Prospect
from ebus.custom_settings.algorithm_settings import HEURISTIC_SETTINGS, WALKING_SETTINGS


class Estimate(NamedTuple):
    travel_time: int
    at_time: int


class Instant(NamedTuple):
    day_type: int
    time: int

    @classmethod
    def from_date(cls, date, time):
        if time > DAY:
            time -= DAY
            date += datetime.timedelta(days=1)

        match date.weekday():
            case 6:
                dt = 2
            case 5:
                dt = 1
            case _:
                dt = 0

        return cls(dt, time)


class Estimator(NamedTuple):
    estimate: Callable[[Stops, Prospect, int, Instant], int]
    time_valid: int


null_estimator = Estimator(
    estimate = lambda stops, prospect, from_stop, at_time: 0,
    time_valid = INF_TIME,
)


def distance_estimator(metric: Callable[[Point, Point], float]) -> Estimator:
    max_speed = HEURISTIC_SETTINGS["MAX_SPEED"]

    @nb.jit
    def estimate(stops, prospect, from_stop, at_time):
        distance = metric(stops[from_stop].position, prospect.destination)
        return distance / max_speed

    return Estimator(estimate, INF_TIME)


@nb.jit
def euclidean_metric(a: Point, b: Point) -> float:
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

euclidean_estimator = distance_estimator(euclidean_metric)


@nb.jit
def manhattan_metric(a: Point, b: Point) -> float:
    return abs(a.x - b.x) + abs(a.y - b.y)

manhattan_estimator = distance_estimator(manhattan_metric)
