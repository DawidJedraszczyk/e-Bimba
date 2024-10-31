insert into gtfs_calendar by name select
  columns(c -> c in (
    'service_id',
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
    'saturday',
    'sunday',
    'start_date',
    'end_date',
  ))
from gtfs_parse_csv('calendar');
