create temp table processed_shape as with
  agg_points as (
    select
      shape_id,
      list(
        struct_pack(lat := shape_pt_lat, lon := shape_pt_lon)
        order by shape_pt_sequence
      ) as points,
    from gtfs_shapes
    group by shape_id
  )

select
  nextval('seq_shape_id') as id,
  list(shape_id) as shape_ids,
  points,
from agg_points
group by points;


create temp table shape_map as select
  id,
  unnest(shape_ids) as shape_id,
from processed_shape;
