insert into stop by name select
  i.*,
  (
    select cluster
    from clustering c
    where c.id = i.id
  ) as cluster,
  (
    select struct_pack(x, y)
    from stop_pos p
    where p.id = i.id
  ) as position,
  (
    select
      coalesce(list(
        struct_pack(to_stop, distance)
        order by distance
      ), []),
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


set variable CENTER = ST_Transform(
  ST_Point2D(getvariable('X0'), getvariable('Y0')),
  getvariable('PROJECTION'),
  'WGS84'
);


insert into metadata values (
  getvariable('CITY'),
  getvariable('REGION'),
  getvariable('PROJECTION'),
  struct_pack(
    lat := ST_X(getvariable('CENTER')),
    lon := ST_Y(getvariable('CENTER'))
  ),
  struct_pack(
    x := getvariable('X0'),
    y := getvariable('Y0')
  ),
  [],
);


create index idx_trip_instance_start_time_service_trip
  on trip_instance (start_time, service, trip);


analyze;
