from pyspark.sql import DataFrame

def write_target(df: DataFrame, contract: dict):
    target = contract["target"]

    writer = (
        df.write
        .mode(target.get("mode", "append"))
        .option("compression", "snappy")
    )

    partitions = target.get("partition_by")
    if partitions:
        writer = writer.partitionBy(partitions)

    writer.parquet(target["path"])
