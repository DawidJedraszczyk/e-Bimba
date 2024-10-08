insert into walk select
  from_stop,
  unnest(list_zip(to_stops, distances), recursive := true),
from walk_calc
order by from_stop;

drop table walk_calc;
