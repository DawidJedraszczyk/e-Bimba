create temp table stop_walk (
  from_stop int4 not null,
  to_stop int4 not null,
  distance int2 not null, -- in meters
);


with
  distances as (
    select
      f.id as from_stop,
      t.id as to_stop,
      ST_Distance(
        ST_Point2D(f.x, f.y),
        ST_Point2D(t.x, t.y)
      ) as distance,
    from stop_pos f
    join stop_pos t on (t.id != f.id)
  ),

  ranked as (
    select
      *,
      rank() over (partition by from_stop order by distance) as rank,
    from distances
  ),

  nearest as (
    select from_stop, to_stop
    from ranked
    where rank <= 10
      or distance <= getvariable('MAX_STOP_WALK')
  )

select
  from_stop,
  first(f.coords).lat as lat,
  first(f.coords).lon as lon,
  list(
    struct_insert(
      t.coords,
      id := to_stop
    )
  ) as to_stops,
from nearest
join imported_stop f on (f.id = from_stop)
join imported_stop t on (t.id = to_stop)
group by from_stop
