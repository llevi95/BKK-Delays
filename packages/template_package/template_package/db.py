# one place that knows how to connect MSSQL and move dataframes in/out

import pandas as pd
from sqlalchemy import create_engine, text

def get_engine(user, password, host, port, database):
    """Build a SQLAlchemy engine for MSSQL via pymssql."""
    url = f"mssql+pymssql://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url)

def ensure_schema(engine, schema = "bkk"):
    """Create the 'bkk' schema if it doesn't exist (idempotent)."""
    with engine.begin() as conn:
        conn.execute(text(
            f"IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = '{schema}') "
            f"EXEC ('CREATE SCHEMA {schema}')"
        ))

def write_df(df, engine, table, schema = "bkk", if_exists="append"):
    """Write a dataframe to a table using pandas to_sql."""
    df.to_sql(table, engine, schema=schema, if_exists=if_exists, index=False)

def read_sql(engine, query, params = None):
    """Read a query result into a DataFrame."""
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params or {})

# idempotency helper. prevents duplicates on daily reruns
def replace_day(engine, schema, table, service_date):
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {schema}.{table} WHERE service_date = :d"),
                     {"d": service_date})