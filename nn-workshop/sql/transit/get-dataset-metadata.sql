install spatial;
load spatial;

with
  term as (
    select
      ord,
      ST_Point2D(lat, lon) as point,
    from values
      (1, 'SOB42'),
      (2, 'JUNI42'),
      (3, 'DEEC42'),
      (4, 'FRWO42'),
      (5, 'MILO42'),
      (6, 'BLAZ42'),
      (7, 'SOB42')
      term(ord, code)
    join stop on (stop.code = term.code)
  ),

  centroid as (
    select
      struct_pack(lat := x, lon := y) as val,
    from (
      select
        unnest(
          ST_Centroid(
            ST_MakePolygon(ST_MakeLine(
              list(point :: geometry order by ord)
            ))
          ) :: point_2d
        ),
      from term
    )
  ),

  max_dev as (
    select
      struct_pack(
        lat := max(abs((select val.lat from centroid) - ST_X(point))),
        lon := max(abs((select val.lon from centroid) - ST_Y(point)))
      ),
    from term
  )

select
  struct_pack(
    centroid := (select * from centroid),
    max_dev := (select * from max_dev)
  )
