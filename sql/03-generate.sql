insert into connection select
  f.stop_id as from_stop,
  f.departure % (24*60*60) as departure,
  t.stop_id,
  (t.arrival - f.departure),
  (select service_id from trip where id = f.trip_id),
  f.departure >= 24*60*60,
  f.trip_id,
from stop_time f
join stop_time t on (f.trip_id = t.trip_id and t.sequence > f.sequence)
where
  f.pickup_type != 1
  and t.drop_off_type != 1
order by from_stop, departure;
