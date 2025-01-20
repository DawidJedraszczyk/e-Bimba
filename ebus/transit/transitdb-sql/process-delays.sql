with
  parsed as (
    select unnest(cast(? as json)[(select name from metadata)]->'$[*]') as value
  ),

  extracted as (
    select
      value->>'trip_id' as trip_id,
      cast(value->'delay' as int4) as delay,
    from parsed
  )

select
  trip,
  service,
  start_time,
  delay,
from extracted
join trip_instance on (gtfs_trip_id = trip_id)
where delay > 0
