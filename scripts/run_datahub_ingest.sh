#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

export PATH="$PROJECT_ROOT/venv/bin:$PATH"
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

METRICS_DIR="$PROJECT_ROOT/monitor/metrics"
METRICS_FILE="$METRICS_DIR/pipeline_runs.jsonl"
mkdir -p "$METRICS_DIR"

START_EPOCH="$(date +%s)"
START_TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
RUN_ID="ingest-$(date +%s)-$RANDOM"
RECORDED=0

record_metric() {
  local status="$1"
  local error_message="${2:-}"
  local end_epoch
  end_epoch="$(date +%s)"
  local duration
  duration=$((end_epoch - START_EPOCH))
  python3 - <<'PY' "$METRICS_FILE" "$RUN_ID" "$START_TS" "$START_EPOCH" "$end_epoch" "$duration" "$status" "$error_message"
import json, sys
path, run_id, start_ts, start_epoch, end_epoch, duration, status, error = sys.argv[1:]
row = {
    "run_id": run_id,
    "pipeline": "run_datahub_ingest",
    "status": status,
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
      record_metric "failed" "run_datahub_ingest_exit_${rc}"
    fi
  fi
  exit "$rc"
}

trap on_exit EXIT

datahub ingest -c scripts/to_datahub.yaml
