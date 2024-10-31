insert into stop by name select
  i.*,
  (
    select
      coalesce(list(
        struct_pack(sw.id, distance)
        order by distance
      ), [])
    from (
      select to_stop as id, distance from stop_walk where from_stop = i.id
      union all
      select from_stop as id, distance from stop_walk where to_stop = i.id
    ) sw
  ) as within_walking,
from imported_stop i;
