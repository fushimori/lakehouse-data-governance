#!/usr/bin/env python3
import json
import os
import time
from collections import defaultdict

from prometheus_client import Gauge, start_http_server


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
METRICS_FILE = os.path.join(PROJECT_ROOT, "monitor", "metrics", "pipeline_runs.jsonl")
PORT = int(os.getenv("LDP_METRICS_EXPORTER_PORT", "9108"))


RUNS_TOTAL = Gauge(
    "ldp_pipeline_runs_total",
    "Total pipeline runs by pipeline and status",
    ["pipeline", "status"],
)
LAST_DURATION = Gauge(
    "ldp_pipeline_last_duration_seconds",
    "Last observed run duration in seconds by pipeline",
    ["pipeline"],
)
LAST_RUN_TS = Gauge(
    "ldp_pipeline_last_run_timestamp_seconds",
    "Last run timestamp (unix epoch) by pipeline",
    ["pipeline"],
)
SUCCESS_RATIO = Gauge(
    "ldp_pipeline_success_ratio",
    "Success ratio in range [0,1] by pipeline",
    ["pipeline"],
)


def load_rows(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def publish(rows: list[dict]) -> None:
    RUNS_TOTAL.clear()
    LAST_DURATION.clear()
    LAST_RUN_TS.clear()
    SUCCESS_RATIO.clear()

    by_pipeline_status: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    last_by_pipeline: dict[str, dict] = {}

    for row in rows:
        pipeline = row.get("pipeline", "unknown")
        status = row.get("status", "unknown")
        by_pipeline_status[pipeline][status] += 1
        last_by_pipeline[pipeline] = row

    for pipeline, status_map in by_pipeline_status.items():
        total = 0
        success = 0
        for status, count in status_map.items():
            RUNS_TOTAL.labels(pipeline=pipeline, status=status).set(count)
            total += count
            if status == "success":
                success += count
        ratio = (success / total) if total else 0.0
        SUCCESS_RATIO.labels(pipeline=pipeline).set(ratio)

    for pipeline, row in last_by_pipeline.items():
        duration = float(row.get("duration_seconds", 0.0))
        end_epoch = float(row.get("end_epoch", 0.0))
        LAST_DURATION.labels(pipeline=pipeline).set(duration)
        LAST_RUN_TS.labels(pipeline=pipeline).set(end_epoch)


def main() -> None:
    os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
    start_http_server(PORT)
    while True:
        rows = load_rows(METRICS_FILE)
        publish(rows)
        time.sleep(15)


if __name__ == "__main__":
    main()
