insert into gtfs_calendar_dates by name select
  columns(c -> c in (
    'service_id',
    'date',
    'exception_type',
  ))
from gtfs_parse_csv('calendar_dates');
