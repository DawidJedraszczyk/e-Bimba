-- Inputs from python variables: from_stop, to_stop, osrm_response

with
  parsed as (
    select
      cast(osrm->'$.distances[0]' as float[])[2:] as distances,
    from (select column0::json as osrm from osrm_response)
  ),

  unnested as (
    select
      generate_subscripts(distances, 1) as i,
      unnest(distances) as distance,
    from parsed
  )

insert into stop_walk select
  f.column0 as from_stop,
  t.id as to_stop,
  u.distance,
from from_stop f
cross join to_stop t
join unnested u on (u.i = t.i)
order by to_stop
