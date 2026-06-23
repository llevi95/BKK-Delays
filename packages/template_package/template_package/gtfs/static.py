# purpose: download the zip and turn the csv into dataframes

import io, zipfile, requests, pandas as pd

#change thes based on file names. used by the parse functions
routes = "routes.txt"
trips = "trips.txt"
stops = "stops.txt"

def download_gtfs_zip(url, api_key, timeout = 60):
    resp = requests.get(url, params={"key": api_key}, timeout = timeout)
    resp.raise_for_status() # raise on http 4xx/5xx
    return zipfile.ZipFile(io.BytesIO(resp.content))

def _read(zf, name, cols):
    with zf.open(name) as f:
        return pd.read_csv(f, usecols = cols)
    
def parse_routes(zf):
    return _read(zf, routes, ["route_id", "route_short_name", "route_long_name", "route_type"])

def parse_trips(zf):
    return _read(zf, trips, ["trip_id", "route_id", "service_id", "trip_headsign"])

def parse_stops(zf):
    return _read(zf, stops, ["stop_id", "stop_name", "stop_lat", "stop_lon"])
    