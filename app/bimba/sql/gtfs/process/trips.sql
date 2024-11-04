create temp table processed_trip as with
  agg_stops as (
    select
      (select id from gtfs_routes r where r.route_id = first(t.route_id)) as route,
      (select id from service_map s where s.service_id = first(t.service_id)) as service,
      (select id from shape_map s where s.shape_id = first(t.shape_id)) as shape,
      coalesce(first(wheelchair_accessible), 0) as wheelchair_accessible,
      list(
        struct_pack(
          stop := (select id from gtfs_stops s where s.stop_id = st.stop_id),
          arrival := time_to_sec(st.arrival_time),
          departure := time_to_sec(st.departure_time),
          st.pickup_type,
          st.drop_off_type
        ) order by st.stop_sequence
      ) as raw_stops,
      raw_stops[1].departure as start_time,
      [
        struct_pack(
          stop := s.stop,
          arrival := s.arrival - start_time,
          departure := s.departure - start_time,
          pickup_type := s.pickup_type,
          drop_off_type := s.drop_off_type
        ) for s in raw_stops
      ] as stops,
    from gtfs_trips t
    join gtfs_stop_times st on (st.trip_id = t.trip_id)
    group by t.trip_id
  ),

  agg_start_times as (
    select
      route,
      service,
      shape,
      list(start_time order by start_time) as start_times,
      stops,
      wheelchair_accessible,
    from agg_stops
    group by all
  ),

  agg_services as (
    select
      route,
      shape,
      list(
        service
        order by service
      ) as services,
      start_times,
      stops,
      wheelchair_accessible,
    from agg_start_times
    group by all
  )

select
  route,
  shape,
  min(start_times[1]) as first_departure,
  max(start_times[-1]) as last_departure,
  list(
    struct_pack(
      services,
      start_times,
      wheelchair_accessible
    ) order by services
  ) as instances,
  stops,
from agg_services
group by all
order by route;
