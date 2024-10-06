insert into agency select
  *,
from read_csv(
  'csv/agency.txt',
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
  'csv/stops.txt',
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
  *,
from read_csv(
  'csv/routes.txt',
  header = true,
  columns = {
    'route_id': 'int4',
    'agency_id': 'int4',
    'route_short_name': 'text',
    'route_long_name': 'text',
    'route_desc': 'text',
    'route_type': 'int1',
    'route_color': 'text',
    'route_text_color': 'text',
  }
)
order by route_id;


insert into trip select
  nextval('trip_id'),
  *,
from (
  select * from read_csv(
    'csv/trips.txt',
    header = true,
    columns = {
      'route_id': 'int4',
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
  'csv/stop_times.txt',
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


copy calendar from 'csv/calendar.txt' (format csv, header, dateformat '%Y%m%d');

copy calendar_date from 'csv/calendar_dates.txt' (format csv, header, dateformat '%Y%m%d');


insert into shape_point select
  shape_id,
  shape_pt_sequence,
  shape_pt_lat,
  shape_pt_lon,
from read_csv(
  'csv/shapes.txt',
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
  'csv/feed_info.txt',
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


insert into connection select
  f.stop_id as from_stop,
  f.departure % (24*60*60) as departure,
  t.stop_id,
  (t.arrival - f.departure),
  (select service_id from trip where id = f.trip_id),
  f.departure >= 24*60*60,
  f.trip_id,
from stop_time f
join stop_time t on (f.trip_id = t.trip_id and t.sequence > f.sequence)
where
  f.pickup_type != 1
  and t.drop_off_type != 1
order by from_stop, departure;

create index connection_from_stop_departure on connection (from_stop, departure);
