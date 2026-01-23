from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

df = spark.read.parquet("data/output/sample/posts/")
df.show(5)
df.printSchema()
