# purpose: fetch the protobuf feed and flatten it into one row per stop-time update.

import requests
import pandas as pd
from datetime import datetime, timezone
from google.transit import gtfs_realtime_pb2


def fetch_trip_updates(url, api_key, timeout=30):
    resp = requests.get(url, params={"key": api_key}, timeout=timeout)
    resp.raise_for_status()
    return resp.content  # raw protobuf bytes


def parse_trip_updates(raw_bytes, ingest_ts=None):
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(raw_bytes)  # decode protobuf
    # NAIVE UTC on purpose: pandas to_sql maps tz-aware datetimes to MSSQL
    # TIMESTAMP (= rowversion), which rejects explicit inserts. Naive -> DATETIME.
    ingest_ts = ingest_ts or datetime.now(timezone.utc).replace(tzinfo=None)
    rows = []
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        tu = entity.trip_update
        trip = tu.trip
        for stu in tu.stop_time_update:
            # BKK sends absolute predicted epoch times (arrival.time / departure.time),
            # NOT delay. Capture the times; delay is computed later by joining with the
            # scheduled times from static GTFS stop_times.txt.
            arr = (
                stu.arrival.time
                if (stu.HasField("arrival") and stu.arrival.HasField("time"))
                else None
            )
            dep = (
                stu.departure.time
                if (stu.HasField("departure") and stu.departure.HasField("time"))
                else None
            )
            rows.append(
                {
                    "ingest_ts": ingest_ts,
                    "service_date": trip.start_date,  # 'YYYYMMDD'
                    "trip_id": trip.trip_id,
                    "route_id": trip.route_id,
                    "stop_id": stu.stop_id,
                    "stop_sequence": stu.stop_sequence,
                    "arrival_time": arr,  # predicted epoch seconds
                    "departure_time": dep,  # predicted epoch seconds
                    "schedule_relationship": trip.schedule_relationship,
                }
            )
    return pd.DataFrame(rows)
