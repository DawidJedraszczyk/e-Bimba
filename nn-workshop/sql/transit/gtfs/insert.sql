insert into agency select
  _tdb_id,
  agency_name,
from gtfs_agency
order by _tdb_id;


insert into stop select
  _tdb_id,
  stop_code,
  stop_name,
  zone_id,
  struct_pack(
    lat := stop_lat,
    lon := stop_lon
  ),
from gtfs_stops
order by _tdb_id;


insert into route select
  _tdb_id,
  (select _tdb_id from gtfs_agency a where a.agency_id = r.agency_id),
  coalesce(route_short_name, route_long_name),
  route_type,
  ('0x' || route_color) :: int4,
  ('0x' || route_text_color) :: int4,
from gtfs_routes r
order by _tdb_id;


insert into trip select
  _tdb_id,
  (select _tdb_id from gtfs_routes r where r.route_id = t.route_id),
  (select _tdb_id from gtfs_uniq_service s where s.service_id = t.service_id),
  (select _tdb_id from gtfs_uniq_shape s where s.shape_id = t.shape_id),
  wheelchair_accessible,
from gtfs_trips t
order by _tdb_id;


create or replace temp macro time_to_sec(time) as
  60*60*cast(time[1:2] as int4)
  + 60*cast(time[4:5] as int4)
  + cast(time[7:8] as int4);

insert into stop_time select
  (select _tdb_id from gtfs_trips t where t.trip_id = st.trip_id) as _tdb_trip,
  stop_sequence,
  (select _tdb_id from gtfs_stops s where s.stop_id = st.stop_id),
  time_to_sec(arrival_time),
  time_to_sec(departure_time),
  pickup_type,
  drop_off_type,
from gtfs_stop_times st
order by _tdb_trip, stop_sequence;


insert into regular_service select
  (select _tdb_id from gtfs_uniq_service u where u.service_id = c.service_id) as _tdb_id,
  [
    monday,
    tuesday,
    wednesday,
    thursday,
    friday,
    saturday,
    sunday,
  ],
  strptime(start_date, '%Y%m%d'),
  strptime(end_date, '%Y%m%d'),
from gtfs_calendar c
order by _tdb_id;


insert into exceptional_service select
  (select _tdb_id from gtfs_uniq_service u where u.service_id = cd.service_id) as _tdb_id,
  strptime(date, '%Y%m%d'),
  exception_type == 1,
from gtfs_calendar_dates cd
order by _tdb_id;


insert into shape_point select
  (select _tdb_id from gtfs_uniq_shape u where u.shape_id = s.shape_id) as _tdb_shape,
  shape_pt_sequence,
  shape_pt_lat,
  shape_pt_lon,
from gtfs_shapes s
order by _tdb_shape, shape_pt_sequence;
