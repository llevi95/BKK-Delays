import pandas as pd
from template_package import transform


def test_categorize_delay_thresholds():
    assert transform.categorize_delay(119) == "on_time"
    assert transform.categorize_delay(120) == "minor_delay"  # not < 120
    assert transform.categorize_delay(300) == "minor_delay"  # <= 300
    assert transform.categorize_delay(301) == "major_delay"
    assert transform.categorize_delay(None) is None


def test_scheduled_epoch_local_conversion():
    # 2026-06-23 08:00 Budapest (CEST, UTC+2). Known UTC epoch
    sd = pd.Series(["20260623"])
    hms = pd.Series(["08:00:00"])
    expected = int(
        pd.Timestamp("2026-06-23 08:00:00", tz="Europe/Budapest").timestamp()
    )
    assert int(transform._scheduled_epoch(sd, hms).iloc[0]) == expected


def test_compute_delays(delays_df):
    d = delays_df.sort_values(["trip_id", "stop_sequence"]).reset_index(drop=True)
    assert d.loc[0, "arrival_delay"] == 30
    assert d.loc[1, "arrival_delay"] == 400
    assert d.loc[2, "arrival_delay"] == 60


def test_primary_delay_falls_back_to_departure():
    row = pd.DataFrame([{"arrival_delay": None, "departure_delay": 99}])
    assert transform.primary_delay(row).iloc[0] == 99


def test_aggregate_daily_trip(delays_df):
    out = transform.aggregate_daily_trip(delays_df).set_index("trip_id")
    assert out.loc["T1", "max_delay"] == 400
    assert out.loc["T1", "samples"] == 2
    assert out.loc["T1", "delay_category"] == "major_delay"
    assert out.loc["T2", "max_delay"] == 60
    assert out.loc["T2", "delay_category"] == "on_time"


def test_aggregate_daily_route(delays_df):
    trip = transform.aggregate_daily_trip(delays_df)
    route = transform.aggregate_daily_route(trip).set_index("route_id")
    # T1 max 400 (>300), T2 max 60, share_over_5min = 1/2
    assert route.loc["R1", "share_over_5min"] == 0.5
    assert route.loc["R1", "delayed_trip_count"] == 1  # only T1 > 120


def test_hourly_buckets(delays_df):
    h = transform.hourly_buckets(delays_df)
    # predicted times ~08:00 and 09:00 local, hours 8 and 9
    assert set(h["hour"]) == {8, 9}
    assert (h["n"] > 0).all()
