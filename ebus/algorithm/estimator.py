from abc import ABC, abstractmethod
import math
from typing import NamedTuple

from transit.data.misc import Point, INF_TIME
from transit.data.stops import Stops
from transit.prospector import NearStop
from ebus.algorithm_settings import HEURISTIC_SETTINGS, WALKING_SETTINGS


class Estimates(NamedTuple):
    travel_time: int
    walk_time: int
    at_time: int


class Estimator(ABC):
    stops: Stops
    destination: Point
    near: list[NearStop]

    TIME_VALID: int = INF_TIME
    PACE: float = WALKING_SETTINGS["PACE"]

    def __init__(
        self,
        stops: Stops,
        destination: Point,
        near: list[NearStop],
    ):
        self.stops = stops
        self.destination = destination
        self.near = near

    @abstractmethod
    def travel_time(self, from_stop: int, at_time: int) -> int:
        pass

    @abstractmethod
    def walk_time(self, from_stop: int) -> int:
        pass


    def estimate_walk_time(self, from_stop: int) -> int:
        for near in self.near:
            if near.id == from_stop:
                return near.walk_distance / self.PACE

        return self.walk_time(from_stop)


    def estimate(self, from_stop: int, at_time: int) -> Estimates:
        return Estimates(
            self.travel_time(from_stop, at_time),
            self.estimate_walk_time(from_stop),
            at_time,
        )


class EuclideanEstimator(Estimator):
    def __init__(
        self,
        stops: Stops,
        destination: Point,
        near: list[NearStop],
    ):
        super().__init__(stops, destination, near)


    def distance(self, a: Point, b: Point) -> float:
        return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)


    def travel_time(self, from_stop: int, at_time: int) -> int:
        distance = self.distance(self.stops[from_stop].position, self.destination)
        return int(distance / HEURISTIC_SETTINGS["MAX_SPEED"])


    def walk_time(self, from_stop: int) -> int:
        distance = self.distance(self.stops[from_stop].position, self.destination)
        return int(distance * WALKING_SETTINGS["DISTANCE_MULTIPLIER"] / self.PACE)


class ManhattanEstimator(Estimator):
    def __init__(
        self,
        stops: Stops,
        destination: Point,
        near: list[NearStop],
    ):
        super().__init__(stops, destination, near)


    def distance(self, a: Point, b: Point) -> float:
        return abs(a.x - b.x) + abs(a.y - b.y)


    def travel_time(self, from_stop: int, at_time: int) -> int:
        distance = self.distance(self.stops[from_stop].position, self.destination)
        return int(distance / HEURISTIC_SETTINGS["MAX_SPEED"])


    def walk_time(self, from_stop: int) -> int:
        distance = self.distance(self.stops[from_stop].position, self.destination)
        return int(distance / self.PACE)
