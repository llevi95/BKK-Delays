import pandas as pd
import pytest
from template_package import quality

def test_download_ok():
    quality.check_download_ok(b"abc")
    with pytest.raises(quality.DataQualityError):
        quality.check_download_ok(b"")

def test_has_records(raw_df):
    quality.check_has_records(raw_df)
    with pytest.raises(quality.DataQualityError):
        quality.check_has_records(pd.DataFrame())

def test_times_numeric_passes(raw_df):
    quality.check_times_numeric(raw_df)

def test_times_numeric_raises_on_garbage(): #edge case faliure
    bad = pd.DataFrame([{"arrival_time": "budapest", "departure_time": 5}])
    with pytest.raises(quality.DataQualityError):
        quality.check_times_numeric(bad)

def test_delay_numeric_passes(delays_df):
    quality.check_delay_numeric(delays_df)

def test_delay_numeric_raises_on_garbage(): #faliure test
    bad = pd.DataFrame([{"arrival_delay": "kecske", "departure_delay": 5}])
    with pytest.raises(quality.DataQualityError):
        quality.check_delay_numeric(bad)

def test_output_not_empty(raw_df):
    quality.check_output_not_empty(raw_df)
    with pytest.raises(quality.DataQualityError):
        quality.check_output_not_empty(pd.DataFrame())
