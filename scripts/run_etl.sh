#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

export PATH="$PROJECT_ROOT/venv/bin:$PATH"
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
export DATAHUB_GMS_URL="${DATAHUB_GMS_URL:-http://localhost:8080}"
export DATAHUB_OPENLINEAGE_ENV="${DATAHUB_OPENLINEAGE_ENV:-PROD}"
# false=сначала OpenLineage (только table lineage), true=сразу SDK (table+column lineage)
export OPENLINEAGE_USE_SDK_ONLY="${OPENLINEAGE_USE_SDK_ONLY:-true}"

METRICS_DIR="$PROJECT_ROOT/monitor/metrics"
METRICS_FILE="$METRICS_DIR/pipeline_runs.jsonl"
mkdir -p "$METRICS_DIR"

START_EPOCH="$(date +%s)"
START_TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
RUN_ID="etl-$(date +%s)-$RANDOM"
CONTRACT_PATH="$1"
DATASET_NAME="$(python3 - <<'PY' "$CONTRACT_PATH"
import os, sys, yaml
path = sys.argv[1]
name = os.path.splitext(os.path.basename(path))[0]
try:
    with open(path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    name = doc.get("dataset", {}).get("name", name)
except Exception:
    pass
print(name)
PY
)"
RECORDED=0

record_metric() {
  local status="$1"
  local error_message="${2:-}"
  local end_epoch
  end_epoch="$(date +%s)"
  local duration
  duration=$((end_epoch - START_EPOCH))
  python3 - <<'PY' "$METRICS_FILE" "$RUN_ID" "$START_TS" "$START_EPOCH" "$end_epoch" "$duration" "$status" "$DATASET_NAME" "$CONTRACT_PATH" "$error_message"
import json, sys
path, run_id, start_ts, start_epoch, end_epoch, duration, status, dataset, contract, error = sys.argv[1:]
row = {
    "run_id": run_id,
    "pipeline": "run_etl",
    "status": status,
    "dataset": dataset,
    "contract_path": contract,
    "start_ts": start_ts,
    "start_epoch": int(start_epoch),
    "end_epoch": int(end_epoch),
    "duration_seconds": int(duration),
}
if error:
    row["error"] = error
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps(row, ensure_ascii=True) + "\n")
PY
  RECORDED=1
}

on_exit() {
  local rc=$?
  if [ "$RECORDED" -eq 0 ]; then
    if [ "$rc" -eq 0 ]; then
      record_metric "success"
    else
      record_metric "failed" "run_etl_exit_${rc}"
    fi
  fi
  exit "$rc"
}

trap on_exit EXIT

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
