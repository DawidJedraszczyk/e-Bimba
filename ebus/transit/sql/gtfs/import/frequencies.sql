insert into gtfs_frequencies by name select
  columns(c -> c in (
    'trip_id',
    'start_time',
    'end_time',
    'headway_secs',
    'exact_times',
  ))
from gtfs_parse_csv('frequencies');
