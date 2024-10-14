create index idx_agency_id on agency (id);
create index idx_stop_id on stop (id);
create index idx_route_id on route (id);
create index idx_trip_id on trip (id);
create index idx_stop_time_trip_id_sequence on stop_time (trip_id, sequence);
create index idx_stop_time_stop_id on stop_time (stop_id);
create index idx_service_id on service (id);
create index idx_shape_point_shape_id_sequence on shape_point (shape_id, sequence);
create index idx_stop_walk_from_stop_to_stop on stop_walk (from_stop, to_stop);
create index idx_connection_from_stop_departure on connection (from_stop, departure);

analyze;
