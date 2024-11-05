create temp table service_map as
  select
    nextval('seq_service_id') :: int4 as id,
    service_id,
  from (
    select service_id from gtfs_calendar
    union
    select service_id from gtfs_calendar_dates
  );
