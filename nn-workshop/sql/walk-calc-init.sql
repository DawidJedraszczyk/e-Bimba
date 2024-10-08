create table walk_calc(
  id int4 not null,
  from_stop int4 not null,
  to_stops int4[] not null,
  coords text not null,
  distances float4[],
);

create temp sequence seq_walk_calc start 1;

with
  stop_coords as (select {'id': id, 'coords': lon || ',' || lat} as stop from stop order by id),
  pairs as (
    select
      f.stop as from,
      t.stop as to,
    from stop_coords f
    join stop_coords t on (t.stop.id > f.stop.id)
  )
insert into walk_calc select
  nextval('seq_walk_calc'),
  "from".id,
  list("to".id order by "to".id),
  "from".coords || ';' || string_agg("to".coords, ';' order by "to".id),
  null,
from pairs
group by "from";

create index idx_walk_calc_id on walk_calc (id);
