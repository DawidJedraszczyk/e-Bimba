create temp table gtfs_agency (
  agency_id text not null default '',
  agency_name text not null,
  agency_url text,
  agency_timezone text,
  agency_lang text,
  agency_phone text,
  agency_fare_url text,
  agency_email text,
);

create temp table gtfs_calendar (
  service_id text not null,
  monday bool not null default false,
  tuesday bool not null default false,
  wednesday bool not null default false,
  thursday bool not null default false,
  friday bool not null default false,
  saturday bool not null default false,
  sunday bool not null default false,
  start_date text not null,
  end_date text not null,
);

create temp table gtfs_calendar_dates (
  service_id text not null,
  date text not null,
  exception_type int1 not null,
);

create temp table gtfs_feed_info (
  feed_publisher_name text,
  feed_publisher_url text,
  feed_lang text,
  default_lang text,
  feed_start_date text,
  feed_end_date text,
  feed_version text,
  feed_contact_email text,
  feed_contact_url text,
);

create temp table gtfs_frequencies (
  trip_id text not null,
  start_time text not null,
  end_time text not null,
  headway_secs int4 not null,
  exact_times int1,
);

create temp table gtfs_routes (
  route_id text not null,
  agency_id text not null default '',
  route_short_name text,
  route_long_name text,
  route_desc text,
  route_type int1 not null,
  route_url text,
  route_color text,
  route_text_color text,
  route_sort_order text,
  continuous_pickup int1,
  continuous_drop_off int1,
  network_id text,
);

create temp table gtfs_shapes (
  shape_id text not null,
  shape_pt_lat float4 not null,
  shape_pt_lon float4 not null,
  shape_pt_sequence int4 not null,
  shape_dist_traveled float4,
);

create temp table gtfs_stop_times (
  trip_id text not null,
  arrival_time text,
  departure_time text,
  stop_id text,
  location_group_id text,
  location_id text,
  stop_sequence int4 not null,
  stop_headsign text,
  start_pickup_drop_off_window text,
  end_pickup_drop_off_window text,
  pickup_type int1,
  drop_off_type int1,
  continuous_pickup int1,
  continuous_drop_off int1,
  shape_dist_traveled float4,
  timepoint int1,
  pickup_booking_rule_id text,
  drop_off_booking_rule_id text,
);

create temp table gtfs_stops (
  stop_id text not null,
  stop_code text,
  stop_name text,
  tts_stop_name text,
  stop_desc text,
  stop_lat float4,
  stop_lon float4,
  zone_id text,
  stop_url text,
  location_type int1,
  parent_station text,
  stop_timezone text,
  wheelchair_boarding int1,
  level_id text,
  platform_code text,
);

create temp table gtfs_trips (
  route_id text not null,
  service_id text not null,
  trip_id text not null,
  trip_headsign text,
  trip_short_name text,
  direction_id int1,
  block_id text,
  shape_id text,
  wheelchair_accessible int1,
  bikes_allowed int1,
);


create or replace temp macro time_to_sec(time) as
  60*60*cast(time[-8:-7] as int4)
  + 60*cast(time[-5:-4] as int4)
  + cast(time[-2:-1] as int4);
