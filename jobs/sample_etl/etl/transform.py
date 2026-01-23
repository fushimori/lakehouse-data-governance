from pyspark.sql.functions import (
    col, coalesce, lit,
    from_unixtime, hour, dayofmonth, month, year
)

def validate_not_null(df, fields):
    for f in fields:
        df = df.filter(col(f).isNotNull())
    return df

def clean_posts(df):
    if "flair" in df.columns:
        df = df.withColumn("flair", coalesce(col("flair"), lit("unknown")))
    return df

def add_time_columns(df, ts_col="created_utc"):
    df = df.withColumn("created_ts", from_unixtime(col(ts_col)).cast("timestamp"))
    df = df.withColumn("hour", hour(col("created_ts")))
    df = df.withColumn("day", dayofmonth(col("created_ts")))
    df = df.withColumn("month", month(col("created_ts")))
    df = df.withColumn("year", year(col("created_ts")))
    return df
