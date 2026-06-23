# one place that knows how to connect MSSQK and write dataframe
from sqlalchemy import create_engine, text

def get_engine(user, password, host, port, database):
    """Build an SQLAchemy engine for MSSQL via pymssql"""
    url = f"mssql+pymssql://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url)

def ensure_schema(engine, schema="bkk"):
    """Create the 'bkk' schema if it doesnt exist"""
    with engine.begin() as conn:
        conn.execuye(text(f"IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = '{schema}') " f"EXEC ('CREATE SCHEMA {schema}')"))

def write_df(df, engine, table, schema="bkk", if_exists="append"):
    """Write a dataframe to a table using pandas to_sql"""
    df.to_sql(table, engine, schema = schema, if_exists=if_exists, index=False)