with
  gathered as materialized (
    select
      f.stop_id as from_stop,
      t.stop_id as to_stop,
      f.departure,
      t.arrival,
      (select service_id from trip where id = f.trip_id) as service_id,
      f.trip_id,
    from stop_time f
    join stop_time t on (f.trip_id = t.trip_id and t.sequence > f.sequence)
    where
      f.pickup_type != 1
      and t.drop_off_type != 1
  ),

  only_best as (
    select *
    from gathered g
    where not exists (
      from gathered b
      where b.from_stop = g.from_stop
        and b.to_stop = g.to_stop
        and b.service_id = g.service_id
        and b.departure >= g.departure
        and b.arrival < g.arrival
    )
  ),

  agg_departures as (
    select
      from_stop,
      to_stop,
      service_id,
      list(
        struct_pack(
          departure,
          arrival,
          trip_id 
        ) order by departure
      ) as departures,
    from only_best
    group by from_stop, to_stop, service_id
  ),

  agg_services as (
    select
      from_stop,
      to_stop,
      list(
        struct_pack(
          service_id,
          departures
        ) order by service_id
      ) as services,
    from agg_departures
    group by from_stop, to_stop
  ),

  with_walk as (
    select
      coalesce(a.from_stop, w.from_stop) as from_stop,
      coalesce(a.to_stop, w.to_stop) as to_stop,
      coalesce(distance, 0) as walk_distance,
      coalesce(services, []) as services,
    from agg_services a
    full join stop_walk w on (w.from_stop = a.from_stop and w.to_stop = a.to_stop)
  )

insert into connections select
  from_stop,
  list(
    struct_pack(
      to_stop,
      walk_distance,
      services
    ) order by to_stop
  ),
from with_walk
group by from_stop
order by from_stop;


drop table stop_walk;
