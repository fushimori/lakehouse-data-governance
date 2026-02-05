#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

export PATH="$PROJECT_ROOT/venv/bin:$PATH"
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

datahub ingest -c scripts/to_datahub.yaml
