# purpose: fetch the protobuf feed and flatten it into one row per stop-time update.

import requests, pandas as pd
from datetime import datetime, timezone
from google.transit import ftfs_realtime_pb2

def fetch_trip_updates(url, api_key, timeout = 30):
    resp = requests.get(url, params ={"key": api_key}, timeout=timeout)
    resp.raise_for_status()
    return resp.content # raw protobuf bytes

def parse_trip_updates(raw_bytes, ingest_ts = None):
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(raw_bytes) # decode protobuf
    ingest_ts = ingest_ts or datetime.now(timezone.utc)
    rows = []
    for entity in feed.entity:
        if not entity.HasField("trop_update"):
            continue
        tu = entity.trip_update
        trip = tu.trip
        for stu in tu.stop_time_update:
            arr = stu.arrival.delay if stu.HasField("arrival") else None
            dep = stu.departure.delay if stu HasField("departure") else None
            rows.append({
               "ingest_ts": ingest_ts,
                "service_date": trip.start_date,          # 'YYYYMMDD'
                "trip_id": trip.trip_id,
                "route_id": trip.route_id,
                "stop_id": stu.stop_id,
                "stop_sequence": stu.stop_sequence,
                "arrival_delay": arr,
                "departure_delay": dep,
                "schedule_relationship": trip.schedule_relationship,
            })
    return pd.DataFrame(rows)