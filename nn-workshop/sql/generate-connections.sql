insert into connection select
  f.stop_id as from_stop,
  f.departure % (24*60*60) as departure,
  t.stop_id as to_stop,
  t.arrival - f.departure as travel_time,
  (select service_id from trip where id = f.trip_id) as service_id,
  f.departure >= 24*60*60 as date_overflow,
  f.trip_id,
from stop_time f
join stop_time t on (f.trip_id = t.trip_id and t.sequence > f.sequence)
where
  f.pickup_type != 1
  and t.drop_off_type != 1
order by from_stop, departure;
