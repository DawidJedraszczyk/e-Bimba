alter table gtfs_agency add column id int4;
update gtfs_agency set id = nextval('seq_agency_id');

alter table gtfs_routes add column id int4;
update gtfs_routes set id = nextval('seq_route_id');

alter table gtfs_stops add column id int4;
update gtfs_stops set id = nextval('seq_stop_id');
