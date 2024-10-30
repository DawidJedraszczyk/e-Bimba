create or replace temp macro gtfs_parse_csv(name) as table (
  select * from read_csv(
      getvariable('GTFS_FOLDER') || '/' || name || '.txt',
      sep = ',',
      quote = '"',
      escape = '"',
      header = true,
      all_varchar = true
    )
  );


insert into gtfs_agency by name select
  columns(c -> c in (
    'agency_id',
    'agency_name',
    'agency_url',
    'agency_timezone',
    'agency_lang',
    'agency_phone',
    'agency_fare_url',
    'agency_email',
  ))
from gtfs_parse_csv('agency');

insert into gtfs_calendar by name select
  columns(c -> c in (
    'service_id',
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
    'saturday',
    'sunday',
    'start_date',
    'end_date',
  ))
from gtfs_parse_csv('calendar');

insert into gtfs_calendar_dates by name select
  columns(c -> c in (
    'service_id',
    'date',
    'exception_type',
  ))
from gtfs_parse_csv('calendar_dates');

insert into gtfs_feed_info by name select
  columns(c -> c in (
    'feed_publisher_name',
    'feed_publisher_url',
    'feed_lang',
    'default_lang',
    'feed_start_date',
    'feed_end_date',
    'feed_version',
    'feed_contact_email',
    'feed_contact_url',
  ))
from gtfs_parse_csv('feed_info');

insert into gtfs_routes by name select
  columns(c -> c in (
    'route_id',
    'agency_id',
    'route_short_name',
    'route_long_name',
    'route_desc',
    'route_type',
    'route_url',
    'route_color',
    'route_text_color',
    'route_sort_order',
    'continuous_pickup',
    'continuous_drop_off',
    'network_id',
  ))
from gtfs_parse_csv('routes');

insert into gtfs_shapes by name select
  columns(c -> c in (
    'shape_id',
    'shape_pt_lat',
    'shape_pt_lon',
    'shape_pt_sequence',
    'shape_dist_traveled',
  ))
from gtfs_parse_csv('shapes');

insert into gtfs_stop_times by name select
  columns(c -> c in (
    'trip_id',
    'arrival_time',
    'departure_time',
    'stop_id',
    'location_group_id',
    'location_id',
    'stop_sequence',
    'stop_headsign',
    'start_pickup_drop_off_window',
    'end_pickup_drop_off_window',
    'pickup_type',
    'drop_off_type',
    'continuous_pickup',
    'continuous_drop_off',
    'shape_dist_traveled',
    'timepoint',
    'pickup_booking_rule_id',
    'drop_off_booking_rule_id',
  ))
from gtfs_parse_csv('stop_times');

insert into gtfs_stops by name select
  columns(c -> c in (
    'stop_id',
    'stop_code',
    'stop_name',
    'tts_stop_name',
    'stop_desc',
    'stop_lat',
    'stop_lon',
    'zone_id',
    'stop_url',
    'location_type',
    'parent_station',
    'stop_timezone',
    'wheelchair_boarding',
    'level_id',
    'platform_code',
  ))
from gtfs_parse_csv('stops');

insert into gtfs_trips by name select
  columns(c -> c in (
    'route_id',
    'service_id',
    'trip_id',
    'trip_headsign',
    'trip_short_name',
    'direction_id',
    'block_id',
    'shape_id',
    'wheelchair_accessible',
    'bikes_allowed',
  ))
from gtfs_parse_csv('trips');
