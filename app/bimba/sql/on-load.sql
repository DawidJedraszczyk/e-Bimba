install spatial;
load spatial;

set variable MD = (
  select struct_pack(
    name,
    projection,
    center
  )
  from metadata
);
