with
  distances as (
    select
      id,
      ST_Distance_Sphere(
        ST_Point2D($lat, $lon),
        ST_Point2D(s.coords.lat, s.coords.lon)
      ) as distance,
    from stop s
    order by distance
  ),

  ranked as (
    select
      *,
      rank() over (order by distance) as rank,
    from distances
  )

select
  id,
from ranked r
where rank <= 5
  or distance <= 1000
