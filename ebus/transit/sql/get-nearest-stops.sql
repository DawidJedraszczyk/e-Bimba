with
  distances as (
    select
      id,
      ST_Distance(
        ST_Point2D($x, $y),
        ST_Point2D(s.position.x, s.position.y)
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
where rank <= $min_count
  or distance <= $radius
