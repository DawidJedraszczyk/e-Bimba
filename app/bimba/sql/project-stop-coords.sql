install spatial;
load spatial;


create temp table stop_pos as
  select
    id,
    x::float4 as x,
    y::float4 as y,
  from (
    select
      id,
      unnest(ST_Transform(ST_Point2D(coords.lat, coords.lon), 'WGS84', getvariable('PROJECTION'))),
    from imported_stop
  )
  order by id;


set variable X0 = (select avg(x)::float4 from stop_pos);
set variable Y0 = (select avg(y)::float4 from stop_pos);


update stop_pos set
  x = x - getvariable('X0'),
  y = y - getvariable('Y0');
