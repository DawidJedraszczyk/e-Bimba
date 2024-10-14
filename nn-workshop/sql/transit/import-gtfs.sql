insert into agency select
  nextval('seq_agency_id'),
  agency_id,
  agency_name,
  agency_url,
  agency_timezone,
  agency_phone,
  agency_lang,
from read_csv('data/gtfs/agency.txt', header = true)
order by agency_id;


insert into stop select
  nextval('seq_stop_id'),
  stop_id,
  stop_code,
  stop_name,
  stop_lat,
  stop_lon,
  zone_id,
from read_csv('data/gtfs/stops.txt', header = true)
order by stop_id;


insert into route select
  nextval('seq_route_id'),
  route_id,
  (select id from agency where src_id = agency_id),
  route_short_name,
  route_long_name,
  route_desc,
  route_type,
  route_color,
  route_text_color,
from read_csv('data/gtfs/routes.txt', header = true)
order by route_id;


create temp table calendar_csv as select
  *,
from read_csv(
  'data/gtfs/calendar.txt',
  header = true,
  dateformat = '%Y%m%d',
  columns = {
    'service_id': 'text',
    'monday': 'bool',
    'tuesday': 'bool',
    'wednesday': 'bool',
    'thursday': 'bool',
    'friday': 'bool',
    'saturday': 'bool',
    'sunday': 'bool',
    'start_date': 'date',
    'end_date': 'date',
  }
);

create temp table calendar_dates_csv as select
  *,
from read_csv(
  'data/gtfs/calendar_dates.txt',
  header = true,
  dateformat = '%Y%m%d',
  columns = {
    'service_id': 'text',
    'date': 'date',
    'exception_type': 'int1',
  }
);

insert into service select
  nextval('seq_service_id'),
  service_id,
from (
  select service_id from calendar_csv
  union
  select service_id from calendar_dates_csv
);

insert into regular_service select
  (select id from service where src_id = service_id) as num_service_id,
  [
    monday,
    tuesday,
    wednesday,
    thursday,
    friday,
    saturday,
    sunday,
  ],
  start_date,
  end_date,
from calendar_csv
order by num_service_id;

insert into exceptional_service select
  (select id from service where src_id = service_id),
  date,
  exception_type == 1,
from calendar_dates_csv;

drop table calendar_csv;
drop table calendar_dates_csv;


create temp table shapes_csv as select
  *,
from read_csv(
  'data/gtfs/shapes.txt',
  header = true,
  columns = {
    'shape_id': 'text',
    'shape_pt_lat': 'float8',
    'shape_pt_lon': 'float8',
    'shape_pt_sequence': 'int4',
  }
);

insert into shape select
  nextval('seq_shape_id'),
  shape_id,
from (select distinct shape_id from shapes_csv order by shape_id);

insert into shape_point select
  (select id from shape where src_id = shape_id) as num_shape_id,
  shape_pt_sequence,
  shape_pt_lat,
  shape_pt_lon,
from shapes_csv
order by num_shape_id, shape_pt_sequence;

drop table shapes_csv;


insert into trip select
  nextval('seq_trip_id'),
  trip_id,
  (select id from route where src_id = route_id),
  (select id from service where src_id = service_id),
  trip_headsign,
  direction_id,
  (select id from shape where src_id = shape_id),
  wheelchair_accessible,
from read_csv('data/gtfs/trips.txt', header = true)
order by trip_id;


create temp macro time_to_sec(time) as
  60*60*cast(time[1:2] as int4)
  + 60*cast(time[4:5] as int4)
  + cast(time[7:8] as int4);

insert into stop_time select
  (select id from trip where src_id = trip_id) as num_trip_id,
  stop_sequence,
  (select id from stop where src_id = stop_id),
  time_to_sec(arrival_time),
  time_to_sec(departure_time),
  stop_headsign,
  pickup_type,
  drop_off_type,
from read_csv('data/gtfs/stop_times.txt', header = true, all_varchar = true)
order by num_trip_id, stop_sequence;


insert into feed_info select
  *,
from read_csv(
  'data/gtfs/feed_info.txt',
  header = true,
  dateformat = '%Y%m%d',
  columns = {
    'feed_publisher_name': 'text',
    'feed_publisher_url': 'text',
    'feed_lang': 'text',
    'feed_start_date': 'date',
    'feed_end_date': 'date',
  }
)
order by feed_publisher_name;


alter table agency drop src_id;
alter table stop drop src_id;
alter table route drop src_id;
alter table trip drop src_id;
alter table service drop src_id;
alter table shape drop src_id;
