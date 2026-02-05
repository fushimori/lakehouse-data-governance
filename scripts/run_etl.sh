#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

export PATH="$PROJECT_ROOT/venv/bin:$PATH"
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

spark-submit \
  --master local[*] \
  --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.1 \
  --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
  --conf spark.sql.catalog.rest=org.apache.iceberg.spark.SparkCatalog \
  --conf spark.sql.catalog.rest.catalog-impl=org.apache.iceberg.rest.RESTCatalog \
  --conf spark.sql.catalog.rest.uri=http://localhost:8181 \
  --conf spark.sql.catalog.rest.io-impl=org.apache.iceberg.hadoop.HadoopFileIO \
  --conf spark.sql.catalog.rest.write.format.default=parquet \
  --conf spark.sql.shuffle.partitions=200 \
  --conf spark.sql.adaptive.enabled=true \
  jobs/sample_etl/main.py \
  --contract "$1"
