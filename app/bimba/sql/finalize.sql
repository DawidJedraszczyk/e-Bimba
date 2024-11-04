insert into stop by name select
  i.*,
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
  ) as trips,
from imported_stop i
