# purpose: the spec asks for basic reliability checks. Each is small function that raises on failure so the corresponding Airflow task turns red and stops bad data flowing downstream

class DataQualityError(Exception):
    pass

def check_download_ok(content):
    if not content:
        raise DataQualityError("Download empty")

def check_has_records(df):
    if df.empty:
        raise DataQualityError("No processable TripUpdates records")

def check_delay_numeric(df):
    bad = ~pd.to_numeric(df["arrival_delay"], errors="coerce").notna() \
          & df["arrival_delay"].notna()
    if bad.any():
        raise DataQualityError("Non-numeric delay values found")

def check_output_not_empty(df):
    if df.empty:
        raise DataQualityError("Aggregated output is empty")