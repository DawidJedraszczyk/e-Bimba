const GTFS_DATA = {
    vehicles_data: [],
    trip_updates_data: []
};

const ws_vehicle_positions = new WebSocket(`ws://${window.location.host}/ws/vehicle_positions/`);

ws_vehicle_positions.onmessage = (event) => {
    GTFS_DATA.vehicles_data = JSON.parse(event.data);
    window.dispatchEvent(new CustomEvent("vehiclePositionsUpdated", { detail: GTFS_DATA.vehicles_data }));
};

const ws_trip_updates = new WebSocket(`ws://${window.location.host}/ws/trip_updates/`);

ws_trip_updates.onmessage = (event) => {
    GTFS_DATA.trip_updates_data = JSON.parse(event.data);
    window.dispatchEvent(new CustomEvent("tripUpdatesUpdated", { detail: GTFS_DATA.trip_updates_data }));
};

