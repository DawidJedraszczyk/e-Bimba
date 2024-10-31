alter table gtfs_agency add column _tdb_id int4;
update gtfs_agency set _tdb_id = nextval('seq_agency_id');

alter table gtfs_routes add column _tdb_id int4;
update gtfs_routes set _tdb_id = nextval('seq_route_id');

alter table gtfs_stops add column _tdb_id int4;
update gtfs_stops set _tdb_id = nextval('seq_stop_id');

alter table gtfs_trips add column _tdb_id int4;
update gtfs_trips set _tdb_id = nextval('seq_trip_id');


create temp table gtfs_uniq_service as
  select
    service_id,
    nextval('seq_service_id') :: int4 as _tdb_id,
  from (
    select service_id from gtfs_calendar
    union
    select service_id from gtfs_calendar_dates
  );


create temp table gtfs_uniq_shape as
  select
    shape_id,
    nextval('seq_shape_id') :: int4 as _tdb_id,
  from (select distinct shape_id from gtfs_shapes);
