create table agency (
  id int4 primary key,
  name text not null,
  url text not null,
  timezone text not null,
  phone text,
  lang text not null,
);

create table stop (
  id int4 primary key,
  code text not null,
  name text not null,
  lat float8 not null,
  lon float8 not null,
  zone text not null,
);

create table route (
  id int4 primary key,
  agency_id int4 not null,
  short_name text not null,
  long_name text not null,
  "desc" text not null,
  "type" int1 not null,
  color text not null,
  text_color text not null,
);

create table trip (
  id int4 primary key,
  route_id int4 not null,
  service_id int2 not null,
  text_id text not null,
  headsign text not null,
  direction_id int1 not null,
  shape_id int4 not null,
  wheelchair_accessible bool not null,
  brigade int4 not null,
);

create sequence trip_id start 1;

create table stop_time (
  trip_id int4 not null,
  sequence int2 not null,
  stop_id int4 not null,
  arrival int4 not null,
  departure int4 not null,
  headsign text not null,
  pickup_type int1 not null,
  drop_off_type int1 not null,
  primary key (trip_id, sequence),
);

create index stop_time_stop_id on stop_time (stop_id);

create table calendar (
  service_id int2 primary key,
  monday bool not null,
  tuesday bool not null,
  wednesday bool not null,
  thursday bool not null,
  friday bool not null,
  saturday bool not null,
  sunday bool not null,
  start_date date not null,
  end_date date not null,
);

create table calendar_date (
  service_id int2 not null,
  date date not null,
  exception_type int1 not null,
);

create table shape_point (
  shape_id int4 not null,
  sequence int4 not null,
  lat float8 not null,
  lon float8 not null,
  primary key (shape_id, sequence),
);

create table feed_info (
  publisher_name text not null,
  publisher_url text not null,
  lang text not null,
  start_date date not null,
  end_date date not null,
);

create table walk (
  from_stop int4 not null,
  to_stop int4 not null,
  distance float4 not null,
  primary key (from_stop, to_stop),
);

create table connection (
  from_stop int4 not null,
  departure int4 not null,
  to_stop int4 not null,
  travel_time int4 not null,
  service_id int2 not null,
  date_overflow bool not null,
  trip_id int4 not null,
);
