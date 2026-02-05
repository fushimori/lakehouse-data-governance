from pyspark.sql import SparkSession
from pyspark.sql.functions import col


def create_spark_session(app_name="DataGovernanceETL"):
    return (
        SparkSession.builder
        .appName(app_name)
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
        )
        .config("spark.sql.catalog.rest", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.rest.catalog-impl", "org.apache.iceberg.rest.RESTCatalog")
        .config("spark.sql.catalog.rest.uri", "http://localhost:8181")
        .config("spark.sql.catalog.rest.io-impl", "org.apache.iceberg.hadoop.HadoopFileIO")
        .config("spark.sql.catalog.rest.write.format.default", "parquet")
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
