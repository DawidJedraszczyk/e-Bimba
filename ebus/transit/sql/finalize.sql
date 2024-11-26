insert into stop by name select
  i.*,
  (
    select struct_pack(x, y)
    from stop_pos p
    where p.id = i.id
  ) as position,
  (
    select
      list(
        struct_pack(to_stop, distance)
        order by distance
      ),
    from stop_walk
    where from_stop = i.id
  ) as walks,
  (
    select
      coalesce(list(
        struct_pack(trip := id, seq, departure)
        order by id
      ), []),
    from (
      select
        id,
        generate_subscripts(stops, 1) - 1 as seq,
        unnest(stops, recursive := true),
      from trip
    ) t
    where t.stop = i.id
      and t.pickup_type != 1
  ) as trips,
from imported_stop i;


insert into metadata values (
  getvariable('CITY'),
  getvariable('REGION'),
  getvariable('PROJECTION'),
  struct_pack(
    x := getvariable('X0'),
    y := getvariable('Y0')
  ),
);


create index idx_trip_instance_start_time_service_trip
  on trip_instance (start_time, service, trip);


analyze;
