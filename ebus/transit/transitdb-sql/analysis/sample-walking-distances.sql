with
  walks as (
    select
      id as from_stop,
      unnest(walks, recursive := true),
    from stop
  ),
  dedup as (
    select
      least(from_stop, to_stop) as a,
      greatest(from_stop, to_stop) as b,
      first(distance) as distance,
    from walks
    group by a, b
  ),
  coords as (
    select
      distance,
      sa.position.x as ax,
      sa.position.y as ay,
      sb.position.x as bx,
      sb.position.y as by,
    from dedup
    join stop sa on (sa.id = a)
    join stop sb on (sb.id = b)
  ),
  distances as (
    select
      distance,
      sqrt((ax - bx)**2 + (ay - by)**2) :: float4 as euclidean,
      abs(ax - bx) + abs(ay - by) as manhattan,
    from coords
  ),
  buckets as (
    select
      floor(distance / 30) :: int2 as bucket,
      list(struct_pack(distance, euclidean, manhattan)) as items,
    from distances
    where distance < 3000 and distance != 0
    group by bucket
  ),
  samples as (
    select
      unnest(items[i])
    from buckets
    cross join (
      select (floor(random()*len(items)) + 1) :: int as i
      from range(10)
    )
  )

select
  distance,
  100 * (euclidean/distance - 1) as euclidean_error,
  100 * (manhattan/distance - 1) as manhattan_error,
from samples
order by distance
