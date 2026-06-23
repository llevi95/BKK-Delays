# purpose: basic reliability checks. Each raises on failure so the matching
# Airflow task turns red and stops bad data flowing downstream.

import pandas as pd

class DataQualityError(Exception):
    pass

def check_download_ok(content):
    if not content:
        raise DataQualityError("Download empty")

def check_has_records(df):
    if df.empty:
        raise DataQualityError("No processable TripUpdates records")

def check_delay_numeric(df):
    for col in ("arrival_delay", "departure_delay"):
        bad = ~pd.to_numeric(df[col], errors="coerce").notna() & df[col].notna()
        if bad.any():
            raise DataQualityError(f"Non-numeric delay values found in {col}")

def check_output_not_empty(df):
    if df.empty:
        raise DataQualityError("Aggregated output is empty")