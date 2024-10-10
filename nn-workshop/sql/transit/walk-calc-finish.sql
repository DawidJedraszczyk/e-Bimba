insert into walk select
  from_stop,
  unnest(to_stops) as to_stop,
  unnest(distances) as distance,
from walk_calc
order by from_stop, to_stop;

drop table walk_calc;
