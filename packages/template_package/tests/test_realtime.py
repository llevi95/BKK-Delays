from pathlib import Path
from template_package.gtfs import realtime

FIXTURE = Path(__file__).parent / "fixtures" / "sample_trip_updates.pb"


def test_parse_trip_updates():
    raw = FIXTURE.read_bytes()
    df = realtime.parse_trip_updates(raw, ingest_ts="2026-06-23T08:00:00Z")
    assert not df.empty
    assert {"trip_id", "route_id", "arrival_time"} <= set(df.columns)
    assert df["trip_id"].iloc[0] == "TRIP_1"
    assert df["arrival_time"].iloc[0] == 1782216827
    assert df["departure_time"].iloc[0] == 1782216873
