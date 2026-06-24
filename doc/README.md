# Documentation of this project (self notes)
## Terminology
- GTFS: General Transit Feed Specification, General Transit Feed Specification. There are static and real-time
- **ctx: parameter accepts arbitrary keyword arguments (like execution dates, task instances, etc.)
- idempotent: you can safely run a query/function multiple times for the same day without doubling the data

## bkk_rt_ingest
### refresh_static_if_stale
At a high level, this function implements a caching pattern for static transit data (GTFS). It checks a database to see when the data was last updated. If it's less than 24 hours old, it skips the update. Otherwise, it downloads a new zip file, parses it, validates it, and overwrites the old database tables.

### fetch_rt
This function is a typical ETL data ingestion step. Its main job is to download real-time transit data, validate it, and write it to a temporary file on a shared filesystem so that subsequent tasks can read it.

XCom workaround: In Airflow, "XComs" allow tasks to pass data to each other. However, Airflow serializes XCom data into JSON, which natively handles text, not raw binary Protobuf data (.pb). To bypass this limitation, the code writes the raw data to a physical file and passes just the file path string to the next task. This works because the tasks run on the same physical server (LocalExecutor) and share a filesystem.

### parse_and_load
This function is the direct sequel to the fetch_rt function. It acts as the downstream Airflow task that pulls the temporary file path, reads the raw binary data, parses it into a structured format, runs data quality checks, appends it to a database table, and finally cleans up the temporary file so it doesn't clutter the server.

## bkk_delay_aggregate

### build_and_load
This function pulls raw data, combines it with scheduled data, computes delay metrics, and saves the summarized results.

### cleanup_raw_data
Because raw tracking data takes up massive disk space, this prevents the database from running out of storage, while preserving your calculated summaries forever.

## db.py
Single data-access layer. One place that knows how to talk to MSSQL. Both DAGs + tests import it instead of repeating SQLAlchemy boilerplate.

## quality.py
Central validation layer. One place for all data-sanity gates. Each function raises DataQualityError on bad data, matching Airflow task turns red, bad data stops before downstream.

## transform.py
Business-logic layer. The actual brains: turns raw rows into delay insights. db.py moves data, quality.py validates it, transform.py computes it.

## conftest.py
Its purpose is to create a small, fake, and predictable dataset (mock data) to test the compute_delays function you just reviewed. This ensures that the math works exactly as expected before deploying the pipeline.

## test_quality.py
Continuation of the testing suite. While the previous snippet set up the fake data, this file contains the actual unit test cases targeting the data validation functions inside the custom quality module.
It relies on a core testing pattern: verifying that valid data passes cleanly and invalid data intentionally crashes (raises an error).

## test_realtime.py
This test reads an actual raw binary Protobuf file (.pb) stored on the disk to make sure the real-world parsing engine (realtime.parse_trip_updates) accurately decodes the feed structure.

## test_transform.py
It acts as the final confirmation that the business logic—such as timezone arithmetic, delay buckets, aggregation math, and fallbacks—is 100% correct by checking specific numeric inputs against expected values.