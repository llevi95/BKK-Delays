"""Ingest DAG: poll BKK GTFS-Realtime TripUpdates, keep static dims fresh, load raw facts."""

import logging
import os
import tempfile
from datetime import datetime, timezone
import pendulum
import requests
from airflow import DAG
from airflow.exceptions import AirflowSkipException
from airflow.operators.python import PythonOperator
from airflow.models import Variable

from template_package import db, quality
from template_package import config
from template_package.gtfs import static, realtime

log = logging.getLogger("airflow.task")

def _engine():
    from airflow.models import Connection
    conn = Connection.get_connection_from_secrets("mssql_default")
    return db.get_engine(conn.get_uri())

def _api_key():
    # key lives in Airflow Variable `bkk_api_key` (set in UI/env)
    # missing key fails loudly instead of leaking a hardcoded one
    return Variable.get("bkk_api_key")

def refresh_static_if_stale():
    eng = _engine()
    db.ensure_schema(eng, "bkk")
    # check freshness, refresh dims at most once a day
    try:
        df = db.read_sql(eng, "SELECT MAX(loaded_at) AS m FROM bkk.routes")
        last = df["m"].iloc[0]
    except Exception:
        last = None
    if last is not None and (pendulum.now("UTC") - pendulum.instance(last)).in_hours() < 24:
        log.info("Static dims fresh; skipping refresh.")
        return
    zf = static.download_gtfs_zip(config.GTFS_ZIP_URL, _api_key())
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive: avoids MSSQL TIMESTAMP/rowversion mapping
    for name, parse in (("routes", static.parse_routes),
                        ("trips", static.parse_trips),
                        ("stops", static.parse_stops)):
        d = parse(zf)
        quality.check_has_records(d)  # non-empty: never replace good dims with junk
        d["loaded_at"] = now
        db.write_df(d, eng, name, schema="bkk", if_exists="replace")
    log.info("Static dims refreshed.")

def fetch_rt(**ctx):
    raw = realtime.fetch_trip_updates(config.TRIP_UPDATES_URL, _api_key())
    quality.check_download_ok(raw)
    # XCom uses a JSON backend, so can't carry raw bytes. Stash protobuf in a temp
    # file (shared host fs under LocalExecutor) and pass the path string instead.
    fd, path = tempfile.mkstemp(prefix="bkk_rt_", suffix=".pb")
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    return path

def parse_and_load(**ctx):
    path = ctx["ti"].xcom_pull(task_ids="fetch_rt")
    with open(path, "rb") as f:
        raw = f.read()
    try:
        df = realtime.parse_trip_updates(raw)
        quality.check_has_records(df)
        quality.check_times_numeric(df)  # raw stores predicted times, not delays
        eng = _engine()
        db.ensure_schema(eng, "bkk")
        db.write_df(df, eng, "stop_time_updates", schema="bkk", if_exists="append")
        log.info("Loaded %d rows into bkk.stop_time_updates", len(df))
    finally:
        os.remove(path)  # clean up temp protobuf

default_args = {
    "owner": "airflow",
    "retries": 3,
    "retry_delay": pendulum.duration(minutes=1),
    "execution_timeout": pendulum.duration(minutes=5),
}

with DAG(
    "bkk_rt_ingest",
    default_args=default_args,
    schedule="*/10 * * * *", ## TODO debatable how often to run
    start_date=pendulum.now("UTC").subtract(hours=1),
    catchup=False,
    max_active_runs=1,
    tags=["bkk", "ingest"],
) as dag:
    t_static = PythonOperator(task_id="refresh_static_if_stale",
                              python_callable=refresh_static_if_stale)
    t_fetch = PythonOperator(task_id="fetch_rt", python_callable=fetch_rt)
    t_load = PythonOperator(task_id="parse_and_load", python_callable=parse_and_load)

    t_static >> t_fetch >> t_load