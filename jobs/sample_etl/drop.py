from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .config(
        "spark.sql.extensions",
        "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
    )
    .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.local.type", "hadoop")
    .config("spark.sql.catalog.local.warehouse", "data/warehouse")
    .getOrCreate()
)

spark.sql("DROP TABLE IF EXISTS local.reddit.comments")
spark.sql("DROP TABLE IF EXISTS local.reddit.posts")

