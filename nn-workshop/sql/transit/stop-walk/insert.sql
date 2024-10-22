-- Inputs from python variables: from_stop, to_stop, osrm_response

with
  parsed as (
    select
      cast(osrm->'$.distances[0]' as float[])[2:] as distances,
      cast(osrm->'$.sources[0].distance' as float) as from_snap,
      cast(osrm->'$.destinations[*].distance' as float[])[2:] as to_snaps,
    from (select column0::json as osrm from osrm_response)
  ),

  unnested as (
    select
      from_snap,
      generate_subscripts(distances, 1) as i,
      unnest(distances) as distance,
      unnest(to_snaps) as to_snap,
    from parsed
  )

insert into stop_walk by name select
  f.column0 as from_stop,
  t.id as to_stop,
  from_snap + u.distance + to_snap as distance,
from from_stop f
cross join to_stop t
join unnested u on (u.i = t.i)
where u.distance <= 2000
order by to_stop
