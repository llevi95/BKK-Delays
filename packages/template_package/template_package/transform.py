# purpose: pure pandas functions that turn raw rows into the business answers.
# These get the most unit tests because they hold the real logic.

import pandas as pd
from template_package.config import ON_TIME_MAX, MINOR_MAX

# GTFS scheduled times are in the agency's local time.
LOCAL_TZ = "Europe/Budapest"


def _hms_to_seconds(hms):
    """'HH:MM:SS' (may exceed 24h) seconds since local midnight."""
    p = hms.str.split(":", expand=True).astype(int)
    return p[0] * 3600 + p[1] * 60 + p[2]


def _scheduled_epoch(service_date, hms):
    """Scheduled local time on service_date, UTC epoch seconds.

    Localizes local midnight then adds the offset as an absolute duration, so
    times past 24h roll into the next day correctly. Returns NaN where missing.
    """
    out = pd.Series(pd.NA, index=hms.index, dtype="Float64")
    mask = hms.notna() & service_date.notna()
    if mask.any():
        base = pd.to_datetime(service_date[mask], format="%Y%m%d").dt.tz_localize(
            LOCAL_TZ
        )
        ts = base + pd.to_timedelta(_hms_to_seconds(hms[mask]), unit="s")
        # resolution-independent epoch seconds (pandas may use us/ns datetime units)
        epoch = (ts - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta("1s")
        out.loc[mask] = epoch.astype("Float64")
    return out


def compute_delays(raw, stop_times):
    """Join predicted RT epoch times with scheduled static times, delay seconds.

    delay = predicted - scheduled (positive = late, negative = early).
    """
    sched = stop_times.rename(
        columns={"arrival_time": "sched_arrival", "departure_time": "sched_departure"}
    )[["trip_id", "stop_sequence", "sched_arrival", "sched_departure"]]
    df = raw.merge(sched, on=["trip_id", "stop_sequence"], how="left")
    arr_sched = _scheduled_epoch(df["service_date"], df["sched_arrival"])
    dep_sched = _scheduled_epoch(df["service_date"], df["sched_departure"])
    df["arrival_delay"] = pd.to_numeric(df["arrival_time"], errors="coerce") - arr_sched
    df["departure_delay"] = (
        pd.to_numeric(df["departure_time"], errors="coerce") - dep_sched
    )
    return df


def primary_delay(df):
    """Pick arrival delay, fall back to departure delay."""
    return df["arrival_delay"].fillna(df["departure_delay"])


def categorize_delay(seconds):
    if seconds is None or pd.isna(seconds):
        return None
    if seconds < ON_TIME_MAX:
        return "on_time"  # < 120s
    if seconds <= MINOR_MAX:
        return "minor_delay"  # 120-300s
    return "major_delay"  # > 300s


def aggregate_daily_trip(df):
    """One row per (service_date, trip_id): max/avg/p95 delay + sample count."""
    d = df.assign(delay=primary_delay(df)).dropna(subset=["delay"])
    g = d.groupby(["service_date", "trip_id", "route_id"])["delay"]
    out = g.agg(
        max_delay="max",
        avg_delay="mean",
        p95=lambda s: s.quantile(0.95),  # value below which 95% of delays fall.
        samples="count",
    ).reset_index()
    out["delay_category"] = out["max_delay"].apply(categorize_delay)
    return out  ## TODO debatable, could use p95, or add separate dimension


def aggregate_daily_route(trip_df):
    """One row per (service_date, route_id): avg/max delay, how many trips, share > 5 min."""
    g = trip_df.groupby(["service_date", "route_id"])
    return g.agg(
        avg_delay=("avg_delay", "mean"),
        max_delay=("max_delay", "max"),
        delayed_trip_count=(
            "max_delay",
            lambda s: (s > ON_TIME_MAX).sum(),
        ),  # how many trips late
        share_over_5min=(
            "max_delay",
            lambda s: (s > MINOR_MAX).mean(),
        ),  # fraction badly late
    ).reset_index()


def hourly_buckets(df):
    """Average delay per local hour-of-day, answers 'when do delays peak?'.

    Bucketed by predicted arrival time (the time the trip actually ran), in
    Europe/Budapest, not by when we happened to poll.
    """
    d = df.assign(delay=primary_delay(df)).dropna(subset=["delay"])
    t = pd.to_numeric(d["arrival_time"], errors="coerce").fillna(
        pd.to_numeric(d["departure_time"], errors="coerce")
    )
    local = pd.to_datetime(t, unit="s", utc=True).dt.tz_convert(LOCAL_TZ)
    d = d.assign(hour=local.dt.hour)
    return (
        d.groupby(["service_date", "hour"])["delay"]
        .agg(avg_delay="mean", n="count")
        .reset_index()
    )
