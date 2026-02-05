from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .config(
        "spark.sql.extensions",
        "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
    )
    .config("spark.sql.catalog.rest", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.rest.catalog-impl", "org.apache.iceberg.rest.RESTCatalog")
    .config("spark.sql.catalog.rest.uri", "http://localhost:8181")
    .config("spark.sql.catalog.rest.io-impl", "org.apache.iceberg.hadoop.HadoopFileIO")
    .config("spark.sql.catalog.rest.write.format.default", "parquet")
    .getOrCreate()
)

df = spark.read.table("rest.reddit.comments")
df.show(5)
df.printSchema()
