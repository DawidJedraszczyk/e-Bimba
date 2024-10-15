# Later departure, earlier arrival

```sql
select
  (select [code, name] from stop where id = c1.from_stop) as f,
  (select [code, name] from stop where id = c1.to_stop) as t,
  (select short_name from route where id = (select route_id from trip where id = c1.trip_id)) as t1,
  fmt_time(c1.departure) as d1,
  fmt_time(c1.arrival) as a1,
  (select short_name from route where id = (select route_id from trip where id = c2.trip_id)) as t2,
  fmt_time(c2.departure) as d2,
  fmt_time(c2.arrival) as a2,
from connection c1
join connection c2 on (c2.from_stop = c1.from_stop and c2.to_stop = c1.to_stop)
where c1.departure < c2.departure
  and c1.arrival > c2.arrival
  and c1.service_id = c2.service_id
order by (c1.arrival - c2.arrival) desc;
```
