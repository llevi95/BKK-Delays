default_args = {"owner": "airflow", "retries": 3,
                "retry_delay": pendulum.duration(minutes=1)}

dag = DAG("bkk_rt_ingest",
          default_args=default_args,
          schedule="*/10 * * * *",
          start_date=pendulum.now("UTC").subtract(hours=1),
          catchup=False, max_active_runs=1,
          tags=["bkk", "ingest"])