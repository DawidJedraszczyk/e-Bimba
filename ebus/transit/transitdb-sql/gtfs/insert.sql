set variable SOURCE_ID = nextval('seq_source_id');

insert into source values (
  getvariable('SOURCE_ID'),
  getvariable('SOURCE_NAME'),
  (select min(date) from covered_days),
  (select max(date) from covered_days),
);


insert into agency select
  id,
  agency_name,
  getvariable('SOURCE_ID'),
from gtfs_agency
order by id;


insert into imported_stop select
  id,
  coalesce(stop_code, ''),
  stop_name,
  coalesce(zone_id, ''),
  struct_pack(
    lat := stop_lat,
    lon := stop_lon
  ),
from gtfs_stops
order by id;


insert into route select
  id,
  coalesce((select id from gtfs_agency a where a.agency_id = r.agency_id), 0),
  coalesce(route_short_name, route_long_name),
  least(route_type, 13),
  coalesce('0x' || route_color, '0xFFFFFF') :: int4,
  coalesce('0x' || route_text_color, '0x000000') :: int4,
from gtfs_routes r
order by id;


insert into trip by name select
  *,
from processed_trip;


insert into trip_instance by name select
  (
    select id from processed_trip pt
    where pt.route = agg.route
      and pt.shape is not distinct from agg.shape
      and pt.headsign is not distinct from agg.headsign
      and pt.stops = agg.stops
  ) as trip,
  service,
  unnest(start_times, recursive := true),
  wheelchair_accessible,
from pt_agg_start_times agg;


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
