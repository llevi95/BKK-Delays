# purpose: download the zip and turn the csv into dataframes

import io
import zipfile
import requests
import pandas as pd

# change thes based on file names. used by the parse functions
routes = "routes.txt"
trips = "trips.txt"
stops = "stops.txt"
stop_times = "stop_times.txt"


def download_gtfs_zip(url, api_key, timeout=60):
    resp = requests.get(url, params={"key": api_key}, timeout=timeout)
    resp.raise_for_status()  # raise on http 4xx/5xx
    return zipfile.ZipFile(io.BytesIO(resp.content))


def _read(zf, name, cols):
    with zf.open(name) as f:
        return pd.read_csv(f, usecols=cols)


def parse_routes(zf):
    return _read(
        zf, routes, ["route_id", "route_short_name", "route_long_name", "route_type"]
    )


def parse_trips(zf):
    return _read(zf, trips, ["trip_id", "route_id", "service_id", "trip_headsign"])


def parse_stops(zf):
    return _read(zf, stops, ["stop_id", "stop_name", "stop_lat", "stop_lon"])


def parse_stop_times(zf):
    # scheduled times per (trip, stop). 'HH:MM:SS' may exceed 24h (e.g. 25:30:00).
    # ~5M rows -> kept in memory for the join, not stored in the DB.
    return _read(
        zf, stop_times, ["trip_id", "stop_sequence", "arrival_time", "departure_time"]
    )
