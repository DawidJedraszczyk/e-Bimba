create type services as struct (
  yesterday int4[],
  today int4[],
  tomorrow int4[]
);


create table agency (
  id int4 not null,
  src_id text not null, -- dropped after import
  name text not null,
  url text not null,
  timezone text not null,
  phone text,
  lang text not null,
);

create sequence seq_agency_id;


create table stop (
  id int4 not null,
  src_id text not null, -- dropped after import
  code text not null,
  name text not null,
  lat float8 not null,
  lon float8 not null,
  zone text not null,
);

create sequence seq_stop_id;


create table route (
  id int4 not null,
  src_id text not null, -- dropped after import
  agency_id int4 not null,
  short_name text not null,
  long_name text not null,
  "desc" text not null,
  "type" int1 not null,
  color text not null,
  text_color text not null,
);

create sequence seq_route_id;


create table trip (
  id int4 not null,
  src_id text not null, -- dropped after import
  route_id int4 not null,
  service_id int4 not null,
  headsign text not null,
  direction_id int1 not null,
  shape_id int4 not null,
  wheelchair_accessible bool not null,
);

create sequence seq_trip_id;


create table stop_time (
  trip_id int4 not null,
  sequence int2 not null,
  stop_id int4 not null,
  arrival int4 not null, -- in seconds after midnight (can be over 86400)
  departure int4 not null, -- also
  headsign text not null,
  pickup_type int1 not null,
  drop_off_type int1 not null,
);


create table service (
  id int4 not null,
  src_id text not null, -- dropped after import
);

create sequence seq_service_id;


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
  src_id text not null, -- dropped after import
);

create sequence seq_shape_id;


create table shape_point (
  shape_id int4 not null,
  sequence int4 not null,
  lat float8 not null,
  lon float8 not null,
);


create table feed_info (
  publisher_name text not null,
  publisher_url text not null,
  lang text not null,
  start_date date not null,
  end_date date not null,
);


create table connections (
  from_stop int4 not null,
  to_stops struct (
    to_stop int4,
    walk_distance int2, -- 0 if too far to walk
    departures struct (
      departure int4,
      arrival int4,
      service_id int4,
      trip_id int4
    )[]
  )[] not null,
);

create view connection as
  select
    from_stop,
    to_stop,
    unnest(departures, recursive := true),
  from (
    select
      from_stop,
      unnest(to_stops, max_depth := 2)
    from connections
  );


create macro parse_time(str) as
  60*60*cast(str[1:2] as int4)
  + 60*cast(str[4:5] as int4);

create macro fmt_time(s) as
  format('{:02d}:{:02d}', s // (60*60), (s // 60) % 60);


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
