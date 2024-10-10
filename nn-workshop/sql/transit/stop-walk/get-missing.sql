install spatial;
load spatial;

with
  stop_coords as materialized (
    select
      {'id': id, 'coords': lon || ',' || lat} as stop,
      ST_Point(lat, lon) as point,
    from stop
    order by id
  ),

  pairs as (
    select
      f.stop as f,
      t.stop as t,
    from stop_coords f
    join stop_coords t on (t.stop.id > f.stop.id)
    where not exists (select * from stop_walk where from_stop = f.stop.id)
      and ST_Distance_Sphere(f.point, t.point) <= 2000
  )

select
  f.id as from_stop,
  list(t.id order by t.id) as to_stops,
  f.coords || ';' || string_agg(t.coords, ';' order by t.id) as coords,
from pairs
group by f
order by from_stop
