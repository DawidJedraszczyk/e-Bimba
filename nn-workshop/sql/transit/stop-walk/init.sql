install spatial;
load spatial;


create temp table stop_walk (
  from_stop int4 not null,
  to_stop int4 not null,
  distance int2 not null, -- in meters
);


select
  f.id,
  unnest(first(f.coords)),
  list(
    struct_pack(
      t.id,
      lat := t.coords.lat,
      lon := t.coords.lon
    )
  ) to_stops,
from stop f
join stop t on (t.id > f.id)
where
  ST_Distance_Sphere(
    ST_Point2D(f.coords.lat, f.coords.lon),
    ST_Point2D(t.coords.lat, t.coords.lon)
  ) <= getvariable('MAX_STOP_WALK')
group by f.id
