insert into agency select
  id,
  agency_name,
from gtfs_agency
order by id;


insert into imported_stop select
  id,
  stop_code,
  stop_name,
  zone_id,
  struct_pack(
    lat := stop_lat,
    lon := stop_lon
  ),
from gtfs_stops
order by id;


insert into route select
  id,
  (select id from gtfs_agency a where a.agency_id = r.agency_id),
  coalesce(route_short_name, route_long_name),
  route_type,
  ('0x' || route_color) :: int4,
  ('0x' || route_text_color) :: int4,
from gtfs_routes r
order by id;


insert into trip by name select
  nextval('seq_trip_id') as id,
  *,
from processed_trip;


insert into regular_service select
  (select id from service_map s where s.service_id = c.service_id) as id,
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
order by id;


insert into exceptional_service select
  (select id from service_map u where u.service_id = cd.service_id) as id,
  strptime(date, '%Y%m%d'),
  exception_type == 1,
from gtfs_calendar_dates cd
order by id;


insert into shape select
  id,
  points,
from processed_shape s
order by id;
