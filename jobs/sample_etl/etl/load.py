from pyspark.sql import DataFrame


def write_target(df: DataFrame, contract: dict):
    target = contract["target"]

    if target.get("format") != "iceberg":
        raise ValueError("Only iceberg format is supported")

    spark = df.sparkSession

    full_table = (
        f"{target['catalog']}."
        f"{target['database']}."
        f"{target['table']}"
    )

    spark.conf.set(
        "spark.sql.iceberg.commit.metadata.contract_version",
        contract.get("version", "unknown")
    )

    df.createOrReplaceTempView("incoming")

    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {full_table}
        USING iceberg
        AS SELECT * FROM incoming WHERE 1 = 0
    """)

    write_mode = target.get("write_mode", "append")

    if write_mode == "upsert":
        pk = target["primary_key"]

        spark.sql(f"""
            MERGE INTO {full_table} t
            USING incoming s
            ON t.{pk} = s.{pk}
            WHEN MATCHED THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *
        """)
    else:
        df.writeTo(full_table).append()
