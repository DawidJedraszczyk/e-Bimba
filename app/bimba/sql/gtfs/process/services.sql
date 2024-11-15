create temp table service_map as
  select
    nextval('seq_service_id') :: int4 as id,
    service_id,
  from (
    select service_id from gtfs_calendar
    union
    select service_id from gtfs_calendar_dates
  );


create temp table covered_days as
  select
    unnest(range(
      strptime(start_date, '%Y%m%d') :: date,
      strptime(end_date, '%Y%m%d') :: date + 1,
      interval 1 day
    )) :: date as date,
  from gtfs_calendar
  union
  select
    strptime(date, '%Y%m%d') :: date as date,
  from gtfs_calendar_dates
  where exception_type == 1;
