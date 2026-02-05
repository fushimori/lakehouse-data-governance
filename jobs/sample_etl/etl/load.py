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

    partitioning = target.get("partitioning", [])
    partition_clause = ""
    if partitioning:
        partition_specs = []
        for part in partitioning:
            field = part.get("field")
            transform = part.get("transform", "identity")
            transform_map = {
                "identity": field,
                "year": f"year({field})",
                "month": f"month({field})",
                "day": f"days({field})",
                "hour": f"hours({field})",
                "bucket": f"bucket({field}, {part.get('buckets', 10)})",
                "truncate": f"truncate({field}, {part.get('width', 10)})"
            }
            
            partition_spec = transform_map.get(transform, field)
            partition_specs.append(partition_spec)
        
        if partition_specs:
            partition_clause = f"PARTITIONED BY ({', '.join(partition_specs)})"

    create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {full_table}
        USING iceberg
        {partition_clause}
        AS SELECT * FROM incoming WHERE 1 = 0
    """
    
    spark.sql(create_table_sql)

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
