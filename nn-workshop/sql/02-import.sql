insert into agency select
  *,
from read_csv(
  'data/gtfs/agency.txt',
  header = true,
  columns = {
    'agency_id': 'int4',
    'agency_name': 'text',
    'agency_url': 'text',
    'agency_timezone': 'text',
    'agency_phone': 'text',
    'agency_lang': 'text',
  }
);


insert into stop select
  *,
from read_csv(
  'data/gtfs/stops.txt',
  header = true,
  columns = {
    'stop_id': 'int4',
    'stop_code': 'text',
    'stop_name': 'text',
    'stop_lat': 'float8',
    'stop_lon': 'float8',
    'zone_id': 'text',
  }
)
order by stop_id;


insert into route select
  nextval('seq_route_id'),
  *,
from read_csv(
  'data/gtfs/routes.txt',
  header = true,
  columns = {
    'route_id': 'text',
    'agency_id': 'int4',
    'route_short_name': 'text',
    'route_long_name': 'text',
    'route_desc': 'text',
    'route_type': 'int1',
    'route_color': 'text',
    'route_text_color': 'text',
  }
);


insert into trip select
  nextval('seq_trip_id'),
  (select id from route where text_id = route_id),
  service_id,
  trip_id,
  trip_headsign,
  direction_id,
  shape_id,
  wheelchair_accessible,
  brigade,
from (
  select * from read_csv(
    'data/gtfs/trips.txt',
    header = true,
    columns = {
      'route_id': 'text',
      'service_id': 'int2',
      'trip_id': 'text',
      'trip_headsign': 'text',
      'direction_id': 'int1',
      'shape_id': 'int4',
      'wheelchair_accessible': 'bool',
      'brigade': 'int4',
    }
  )
  order by trip_id
);


create temp macro time_to_sec(time) as
  60*60*cast(time[1:2] as int4)
  + 60*cast(time[4:5] as int4)
  + cast(time[7:8] as int4);

insert into stop_time select
  (select id from trip where text_id = trip_id) as num_trip_id,
  stop_sequence,
  stop_id,
  time_to_sec(arrival_time),
  time_to_sec(departure_time),
  stop_headsign,
  pickup_type,
  drop_off_type,
from read_csv(
  'data/gtfs/stop_times.txt',
  header = true,
  columns = {
    'trip_id': 'text',
    'arrival_time': 'text',
    'departure_time': 'text',
    'stop_id': 'int4',
    'stop_sequence': 'int2',
    'stop_headsign': 'text',
    'pickup_type': 'int1',
    'drop_off_type': 'int1',
  }
)
order by num_trip_id, stop_sequence;


copy calendar from 'data/gtfs/calendar.txt' (
    format csv,
    header,
    dateformat '%Y%m%d'
);

copy calendar_date from 'data/gtfs/calendar_dates.txt' (
  format csv,
  header,
  dateformat '%Y%m%d'
);


insert into shape_point select
  shape_id,
  shape_pt_sequence,
  shape_pt_lat,
  shape_pt_lon,
from read_csv(
  'data/gtfs/shapes.txt',
  header = true,
  columns = {
    'shape_id': 'int4',
    'shape_pt_lat': 'float8',
    'shape_pt_lon': 'float8',
    'shape_pt_sequence': 'int4',
  }
)
order by shape_id, shape_pt_sequence;


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
