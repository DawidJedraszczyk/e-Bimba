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
