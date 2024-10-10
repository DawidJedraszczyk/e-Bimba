-- Inputs from python variables: coords, osrm_response

with
  parsed as (
    select
      cast(osrm->'distances' as float[][]) as distances,
      cast(osrm->'$.sources[*].distance' as float[]) as snap_distances,
      from (select column0::json as osrm from osrm_response)
  ),

  unnested as materialized (
    select
      generate_subscripts(distances, 1) as i,
      unnest(distances) as distances,
      unnest(snap_distances) as snap_distance,
    from parsed
  )

insert into walk select
  [ca.lat, ca.lon],
  [cb.lat, cb.lon],
  ua.distances[cb.i] + ua.snap_distance + ub.snap_distance,
from coords ca
join unnested ua on (ua.i = ca.i)
join coords cb on (cb.i > ca.i)
join unnested ub on (ub.i = cb.i)
