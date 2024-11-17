install spatial;
load spatial;


create temp table stop_pos as
  select
    id,
    x::float4 as x,
    y::float4 as y,
  from (
    select
      id,
      unnest(ST_Transform(ST_Point2D(coords.lat, coords.lon), 'WGS84', getvariable('PROJECTION'))),
    from imported_stop
  )
  order by id;

set variable X0 = (select avg(x)::float4 from stop_pos);
set variable Y0 = (select avg(y)::float4 from stop_pos);


insert into stop by name select
  i.*,
  (
    select
      struct_pack(
        x := x - getvariable('X0'),
        y := y - getvariable('Y0')
      )
    from stop_pos p
    where p.id = i.id
  ) as position,
  (
    select
      coalesce(list(
        struct_pack(to_stop := sw.id, distance)
        order by distance
      ), [])
    from (
      select to_stop as id, distance from stop_walk where from_stop = i.id
      union all
      select from_stop as id, distance from stop_walk where to_stop = i.id
    ) sw
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
  getvariable('PROJECTION'),
  struct_pack(
    x := getvariable('X0'),
    y := getvariable('Y0')
  ),
);
