"""Aggregate DAG: build daily business tables from raw RT snapshots."""

import logging
import pendulum
from airflow import DAG
from airflow.exceptions import AirflowSkipException
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from template_package import db, quality, transform, config
from template_package.gtfs import static

log = logging.getLogger("airflow.task")

def _engine():
    from airflow.models import Connection
    conn = Connection.get_connection_from_secrets("mssql_default")
    return db.get_engine(conn.get_uri())


def _api_key():
    return Variable.get("bkk_api_key")

def _service_date(ctx):
    # logical date of the run. Aggregate that day. Format matches RT 'YYYYMMDD'
    return ctx["logical_date"].format("YYYYMMDD")

def build_and_load(**ctx):
    sd = _service_date(ctx)
    eng = _engine()
    # raw fact table is created by bkk_rt_ingest on its first write.
    # if aggregate runs first, the table is absent -> skip, don't crash.
    try:
        raw = db.read_sql(
            eng,
            "SELECT * FROM bkk.stop_time_updates WHERE service_date = :d",
            {"d": sd},
        )
    except ProgrammingError:
        raise AirflowSkipException(
            "bkk.stop_time_updates missing — run bkk_rt_ingest first"
        )
    if raw.empty:
        raise AirflowSkipException(f"No raw rows for service_date={sd}")
    quality.check_has_records(raw)

    # delay = predicted (RT) - scheduled (static). Pull scheduled times from the
    # GTFS zip in memory (too big for the DB), filtered to the trips we observed.
    zf = static.download_gtfs_zip(config.GTFS_ZIP_URL, _api_key())
    stop_times = static.parse_stop_times(zf)
    stop_times = stop_times[stop_times["trip_id"].isin(raw["trip_id"].unique())] # for perf opt
    delays = transform.compute_delays(raw, stop_times)
    quality.check_delay_numeric(delays)

    trip = transform.aggregate_daily_trip(delays)
    route = transform.aggregate_daily_route(trip)
    hourly = transform.hourly_buckets(delays)
    for d in (trip, route, hourly):
        quality.check_output_not_empty(d)

    db.ensure_schema(eng, "bkk")
    with eng.begin() as conn:
        for d, table in ((trip, "daily_trip_delays"),
                         (route, "daily_route_delays"),
                         (hourly, "daily_hourly_delays")):
            try:
                db.replace_day(conn, "bkk", table, sd)   # idempotent per day
            except ProgrammingError:
                pass  # table not created yet on first ever run. to_sql makes it below
            db.write_df(d, conn, table, schema="bkk", if_exists="append")
    log.info("Aggregates written for service_date=%s", sd)

def cleanup_raw_data(**ctx):
    sd = _service_date(ctx)
    cutoff_date = pendulum.parse(sd).subtract(days=14).format("YYYYMMDD")
    eng = _engine()
    with eng.begin() as conn:
        try:
            conn.execute(
                text("DELETE FROM bkk.stop_time_updates WHERE service_date < :cutoff"),
                {"cutoff": cutoff_date}
            )
            log.info("Deleted raw data older than %s", cutoff_date)
        except ProgrammingError:
            pass # Table might not exist

default_args = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=2),
    "execution_timeout": pendulum.duration(minutes=10),
}

with DAG(
    "bkk_delay_aggregate",
    default_args=default_args,
    schedule="0 1 * * *", # once a day at 1am
    start_date=pendulum.now("UTC").subtract(days=1),
    catchup=False,
    max_active_runs=1,
    tags=["bkk", "aggregate"],
) as dag:
    t_build = PythonOperator(task_id="build_and_load", python_callable=build_and_load)
    t_clean = PythonOperator(task_id="cleanup_raw_data", python_callable=cleanup_raw_data)
    
    t_build >> t_clean