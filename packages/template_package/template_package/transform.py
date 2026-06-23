# purpose: pure pandas functions that turn raw rows into the business answers.
# These get the most unit tests because they hold the real logic.

import pandas as pd
from template_package.config import ON_TIME_MAX, MINOR_MAX

def primary_delay(df):
    """Pick arrival delay, fall down to departure delay."""
    return df["arrival_delay"].fillna(df["departure_delay"])

def categorize_delay(seconds):
    if seconds is None: return None
    if seconds < ON_TIME_MAX: return "on_time" # < 120s
    if seconds <= MINOR_MAX: return "minor_delay" # 123-300s
    return "major_delay" # > 300s

def aggregate_daily_trip(df):
    """One row per (service_date, trip_id): max/avg/p95 delay + sample count."""
    d = df.assign(delay = primary_delay(df)).dropna(subset = ["delay"])
    g = d.groupby(["service_date", "trip_id", "route_id"])["delay"]
    out = g.agg(max_delay = "max", avg_delay = "mean",
                p95 = lambda s: s.quantile(0.95), samples = "count").reset_index()
    out["delay_category"] = out["max_delay"].apply(categorize_delay)
    return out

def aggregate_daily_route(trip_df):
    """One row per (service_date, route_id): avg/max delay, how many trips, share > 5 min."""
    g = trip_df.groupby(["service_date", "route_id"])
    return g.agg(
        avg_delay=("avg_delay", "mean"),
        max_delay=("max_delay", "max"),
        delayed_trip_count=("max_delay", lambda s: (s > ON_TIME_MAX).sum()), # how many trips late
        share_over_5min=("max_delay", lambda s: (s > MINOR_MAX).mean()), # fraction badly late
    ).reset_index()

def hourly_buckets(df):
    """Average delay per hour of day -> answers 'when do delays peak?'."""
    d = df.assign(delay=primary_delay(df)).dropna(subset=["delay"])
    d["hour"] = pd.to_datetime(d["ingest_ts"]).dt.hour # 0-23
    return d.groupby([d["service_date"], "hour"])["delay"].agg(
        avg_delay="mean", n="count").reset_index()