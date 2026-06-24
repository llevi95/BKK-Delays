import pandas as pd
import pytest

TZ = "Europe/Budapest"

def _epoch(service_date, hms):
    """Local scheduled time -> UTC epoch seconds (mirrors transform._scheduled_epoch)."""
    h, m, s = map(int, hms.split(":"))
    midnight = pd.Timestamp(f"{service_date[:4]}-{service_date[4:6]}-{service_date[6:]}", tz=TZ)
    return int(midnight.timestamp()) + h * 3600 + m * 60 + s

SD = "20260623"

@pytest.fixture
def stop_times_df():
    return pd.DataFrame([
        {"trip_id": "T1", "stop_sequence": 1, "arrival_time": "08:00:00", "departure_time": "08:00:00"},
        {"trip_id": "T1", "stop_sequence": 2, "arrival_time": "08:05:00", "departure_time": "08:05:00"},
        {"trip_id": "T2", "stop_sequence": 1, "arrival_time": "09:00:00", "departure_time": "09:00:00"},
    ])

@pytest.fixture
def raw_df():
    # predicted epoch times = scheduled + a known delay; two trips, one route
    return pd.DataFrame([
        {"ingest_ts": "2026-06-23T06:00:00Z", "service_date": SD,
         "trip_id": "T1", "route_id": "R1", "stop_id": "S1", "stop_sequence": 1,
         "arrival_time": _epoch(SD, "08:00:00") + 30, "departure_time": _epoch(SD, "08:00:00") + 30,
         "schedule_relationship": 0},
        {"ingest_ts": "2026-06-23T06:10:00Z", "service_date": SD,
         "trip_id": "T1", "route_id": "R1", "stop_id": "S2", "stop_sequence": 2,
         "arrival_time": _epoch(SD, "08:05:00") + 400, "departure_time": _epoch(SD, "08:05:00") + 400,
         "schedule_relationship": 0},
        {"ingest_ts": "2026-06-23T07:00:00Z", "service_date": SD,
         "trip_id": "T2", "route_id": "R1", "stop_id": "S1", "stop_sequence": 1,
         "arrival_time": _epoch(SD, "09:00:00") + 60, "departure_time": None,
         "schedule_relationship": 0},
    ])

@pytest.fixture
def delays_df(raw_df, stop_times_df):
    from template_package import transform
    return transform.compute_delays(raw_df, stop_times_df)
