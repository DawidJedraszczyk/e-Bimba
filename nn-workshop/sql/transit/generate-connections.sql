with
  gathered as (
    select
      f.stop as from_stop,
      t.stop as to_stop,
      (select service from trip where id = f.trip) as service,
      list(
        struct_pack(
          f.departure,
          t.arrival,
          f.trip
        ) order by f.departure
      ) as times,
    from stop_time f
    join stop_time t on (f.trip = t.trip and t.sequence > f.sequence)
    where
      f.pickup_type != 1
      and t.drop_off_type != 1
    group by from_stop, to_stop, service
  ),

  only_best as (
    select
      from_stop,
      to_stop,
      service,
      [
        x for x, i in times
        if coalesce(x.arrival < list_min([y.arrival for y in times[i+1:]]), true)
      ] as times,
    from gathered
  ),

  agg_services as (
    select
      from_stop,
      to_stop,
      map_from_entries(list(
        struct_pack(k := service, v:= times)
      )) as s_map,
      [
        flatten(s_map[i])
        for i in range(
          (select max(id) from (
            select id from regular_service
            union all select id from exceptional_service)
          ) + 1
        )
      ] as services,
    from only_best b
    group by from_stop, to_stop
  ),

  with_stop_info as (
    select
      f.id as from_stop,
      t.id as to_stop,
      (w.distance / getvariable('WALK_SPEED')) :: int2 as walk_time,
      list_min([s[1].arrival for s in services]) as first_arrival,
      list_max([s[-1].departure for s in services]) as last_departure,
      services,
    from stop f
    cross join stop t
    left join stop_walk w on (
      w.from_stop = least(f.id, t.id)
      and
      w.to_stop = greatest(f.id, t.id)
    )
    left join agg_services a on (
      a.from_stop = f.id
      and
      a.to_stop = t.id
    )
    where w.distance is not null
      or services is not null
  )

insert into connections select
  from_stop,
  coalesce(list(
    struct_pack(
      to_stop,
      walk_time := greatest(walk_time, -1) + 1,
      first_arrival := coalesce(first_arrival, 0),
      last_departure := coalesce(last_departure, 0),
      services := coalesce(services, [])
    ) order by to_stop
  ), []),
from stop f
left join with_stop_info on (from_stop = f.id)
group by from_stop
order by from_stop;


drop table stop_walk;
