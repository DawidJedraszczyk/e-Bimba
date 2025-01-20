create temp table pt_agg_stops as with
  raw as (
    select
      t.trip_id as id,
      (select id from gtfs_routes r where r.route_id = trim(first(t.route_id))) as route,
      (select id from service_map s where s.service_id = first(t.service_id)) as service,
      (select id from shape_map s where s.shape_id = first(t.shape_id)) as shape,
      first(trip_headsign) as headsign,
      coalesce(first(wheelchair_accessible), 0) as wheelchair_accessible,
      list(
        struct_pack(
          stop := (select id from gtfs_stops s where s.stop_id = st.stop_id),
          arrival := time_to_sec(st.arrival_time),
          departure := time_to_sec(st.departure_time),
          pickup_type := coalesce(st.pickup_type, 0),
          drop_off_type := coalesce(st.drop_off_type, 0)
        ) order by st.stop_sequence
      ) as stops,
    from gtfs_trips t
    join gtfs_stop_times st on (st.trip_id = t.trip_id)
    group by t.trip_id
  )
select
  id,
  route,
  service,
  shape,
  headsign,
  wheelchair_accessible,
  stops[1].departure as start_time,
  [
    struct_pack(
      stop := s.stop,
      arrival := s.arrival - start_time,
      departure := s.departure - start_time,
      pickup_type := s.pickup_type,
      drop_off_type := s.drop_off_type
    ) for s in stops
  ] as stops,
from raw;


create table pt_agg_start_times as select
  route,
  service,
  shape,
  headsign,
  wheelchair_accessible,
  list(struct_pack(start_time, gtfs_trip_id := id)) as start_times,
  stops,
from pt_agg_stops
where not exists (from gtfs_frequencies f where f.trip_id = id)
group by all;


insert into pt_agg_start_times select
  route,
  service,
  shape,
  headsign,
  wheelchair_accessible,
  reduce(
    list([
      struct_pack(start_time := t, gtfs_trip_id := id)
      for t in range(parse_time(f.start_time), parse_time(end_time), headway_secs)
    ]),
    (xs, ys) -> xs || ys
  ),
  stops,
from pt_agg_stops
join gtfs_frequencies f on (f.trip_id = id)
group by all;


drop table pt_agg_stops;


create temp table processed_trip as with
  sorted as (
    select
      route,
      service,
      shape,
      headsign,
      list_sort([st.start_time for st in start_times]) as start_times,
      stops,
    from pt_agg_start_times
  ),

  agg_services as (
    select
      route,
      shape,
      headsign,
      list(
        service
        order by service
      ) as services,
      start_times,
      stops,
    from sorted
    group by all
  ),

  agg_starts as (
    select
      route,
      shape,
      headsign,
      min(start_times[1]) as first_departure,
      max(start_times[-1]) as last_departure,
      list(
        struct_pack(
          services,
          times := start_times
        ) order by services
      ) as starts,
      stops,
    from agg_services
    group by all
    order by route
  )

select
  nextval('seq_trip_id') as id,
  *,
from agg_starts;
