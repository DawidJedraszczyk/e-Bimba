from ebus.custom_settings.algorithm_settings import *

class Preferences:
  pace: float
  start_radius: int
  start_min_count: int
  destination_radius: int
  destination_min_count: int
  max_stop_walk: int

  def __init__(
    self,
    pace = None,
    max_distance = None,
    start_radius = None,
    start_min_count = None,
    destination_radius = None,
    destination_min_count = None,
    max_stop_walk = None,
  ):
    self.pace = pace or WALKING_SETTINGS["PACE"]
    self.start_radius = start_radius or max_distance or PROSPECTING_SETTINGS["START_RADIUS"]
    self.start_min_count = start_min_count or PROSPECTING_SETTINGS["START_MIN_COUNT"]
    self.destination_radius = destination_radius or max_distance or PROSPECTING_SETTINGS["DESTINATION_RADIUS"]
    self.destination_min_count = destination_min_count or PROSPECTING_SETTINGS["DESTINATION_MIN_COUNT"]
    self.max_stop_walk = max_stop_walk or max_distance or 10000000
