with
  days as (
    select range :: date as date
    from range(
      (select max(min_date) from source),
      (select min(max_date) from source) + 1,
      interval 1 day
    )
  ),
  with_services as (
    select
      date,
      case
        when dayofweek(date) = 0 then 2
        when dayofweek(date) = 6 then 1
        else 0
      end as day_type,
      get_service_list(date) as services,
    from days
  ),
  counted as (
    select
      day_type,
      services,
      count(*) as count,
    from with_services
    group by day_type, services
  )
select
  day_type,
  first(services order by count desc) as services,
from counted
group by day_type
order by day_type
