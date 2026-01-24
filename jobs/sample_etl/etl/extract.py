from pyspark.sql import SparkSession
from pyspark.sql.functions import col


def create_spark_session(app_name="DataGovernanceETL"):
    return (
        SparkSession.builder
        .appName(app_name)
        # Iceberg extensions
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
        )
        # Local Hadoop catalog
        .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.local.type", "hadoop")
        .config("spark.sql.catalog.local.warehouse", "data/warehouse")
        # Spark tuning
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
