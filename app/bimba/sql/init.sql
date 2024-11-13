create table metadata (
  name text not null,
  projection text not null,
  center struct (
    x float4,
    y float4
  ) not null,
);


create table agency (
  id int4 not null,
  name text not null,
);

create sequence seq_agency_id minvalue 0 start 0;


create table stop (
  id int4 not null,
  code text,
  name text not null,
  zone text,

  coords struct (
    lat float4,
    lon float4
  ) not null,

  position struct ( -- in meters, relative to metadata.center
    x float4,
    y float4
  ) not null,

  walks struct (
    to_stop int4,
    distance int2
  )[] not null,

  trips struct (
    trip int4,
    seq int2,
    departure int4
  )[] not null,
);

create temp table imported_stop (
  id int4 not null,
  code text,
  name text not null,
  zone text,

  coords struct (
    lat float4,
    lon float4
  ) not null,
);

create sequence seq_stop_id minvalue 0 start 0;


create table route (
  id int4 not null,
  agency int4 not null,
  name text not null,
  type int1 not null,
  color int4,
  text_color int4,
);

create sequence seq_route_id minvalue 0 start 0;


create table trip (
  id int4 not null,
  route int4 not null,
  shape int4,
  headsign text,
  first_departure int4 not null,
  last_departure int4 not null,

  instances struct (
    services int4[],
    start_times int4[],
    wheelchair_accessible int1
  )[] not null,

  stops struct (
    stop int4,
    arrival int4, -- in seconds after midnight (can be over 86400)
    departure int4, -- also
    pickup_type int1,
    drop_off_type int1
  )[] not null,
);

create sequence seq_trip_id minvalue 0 start 0;


create sequence seq_service_id minvalue 0 start 0;

create table regular_service (
  id int4 not null,
  weekday bool[7] not null, -- weekdays during which this service is operating (mon - sun)
  start_date date not null,
  end_date date not null,
);

create table exceptional_service (
  id int4 not null,
  date date not null,
  available bool not null,
);


create table shape (
  id int4 not null,
  points struct (
    lat float4,
    lon float4
  )[] not null,
);

create sequence seq_shape_id minvalue 0 start 0;


create macro parse_time(str) as
  60*60*cast(str[1:2] as int4)
  + 60*cast(str[4:5] as int4);

create macro fmt_time(s) as
  format('{:02d}:{:02d}', s // (60*60), (s // 60) % 60);


create type services as struct (
  yesterday int4[],
  today int4[],
  tomorrow int4[]
);


create macro get_services(date) as table
  select id
  from regular_service
  where date >= start_date
    and date <= end_date
    and weekday[(dayofweek(date::date) + 6) % 7 + 1]
    and not exists (
      select * from exceptional_service e
      where e.date = date
        and not available
    )
  union
  select id
  from exceptional_service e
  where e.date = date
    and available;


create macro get_service_list(day) as (
  select coalesce(list(id), []) from get_services(day::date)
);


create macro get_service_lists(middle) as {
  'yesterday': get_service_list(middle::date - 1),
  'today': get_service_list(middle),
  'tomorrow': get_service_list(middle::date + 1),
};
