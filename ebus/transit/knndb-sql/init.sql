create table data as select
  [
    from_x,
    from_y,
    to_x,
    to_y,
    day_type,
    start,
  ]::float4[6] as inputs,
  time as output,
from read_parquet(getvariable('SRC'));

SET hnsw_enable_experimental_persistence = true;
create index idx_data_inputs on data using hnsw(inputs);
