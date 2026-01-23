from pyspark.sql import SparkSession
from pyspark.sql.functions import col

def create_spark_session(app_name="DataGovernanceETL"):
    return (
        SparkSession.builder
        .appName(app_name)
        .config("spark.sql.shuffle.partitions", 200)
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )

def read_dataset(spark: SparkSession, contract: dict):
    dataset = contract["dataset"]
    df = (
        spark.read
        .option("multiline", dataset.get("multiline", False))
        .json(dataset["location"])
    )

    columns = contract["schema"]
    select_exprs = [
        col(src).alias(dst) for dst, src in columns.items()
    ]

    return df.select(*select_exprs)
