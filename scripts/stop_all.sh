#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "🛑 Остановка всех сервисов платформы"
echo "=========================================="
echo ""

if [ -f "$PROJECT_ROOT/.airflow.pid" ]; then
    AIRFLOW_PID=$(cat "$PROJECT_ROOT/.airflow.pid")
    if ps -p "$AIRFLOW_PID" > /dev/null 2>&1; then
        echo "Остановка Airflow (PID: $AIRFLOW_PID)..."
        kill "$AIRFLOW_PID" 2>/dev/null || true
        rm "$PROJECT_ROOT/.airflow.pid"
    fi
fi

if [ -f "$PROJECT_ROOT/.backend.pid" ]; then
    BACKEND_PID=$(cat "$PROJECT_ROOT/.backend.pid")
    if ps -p "$BACKEND_PID" > /dev/null 2>&1; then
        echo "Остановка Backend (PID: $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
        rm "$PROJECT_ROOT/.backend.pid"
    fi
fi

if [ -f "$PROJECT_ROOT/.frontend.pid" ]; then
    FRONTEND_PID=$(cat "$PROJECT_ROOT/.frontend.pid")
    if ps -p "$FRONTEND_PID" > /dev/null 2>&1; then
        echo "Остановка Frontend (PID: $FRONTEND_PID)..."
        kill "$FRONTEND_PID" 2>/dev/null || true
        rm "$PROJECT_ROOT/.frontend.pid"
    fi
fi

if [ -f "$PROJECT_ROOT/.metrics_exporter.pid" ]; then
    METRICS_EXPORTER_PID=$(cat "$PROJECT_ROOT/.metrics_exporter.pid")
    if ps -p "$METRICS_EXPORTER_PID" > /dev/null 2>&1; then
        echo "Остановка Metrics exporter (PID: $METRICS_EXPORTER_PID)..."
        kill "$METRICS_EXPORTER_PID" 2>/dev/null || true
    fi
    rm -f "$PROJECT_ROOT/.metrics_exporter.pid"
fi

echo "Остановка процессов на портах..."

if lsof -ti:8070 >/dev/null 2>&1; then
    echo "Остановка Airflow на порту 8070..."
    pkill -f "airflow.*8070" 2>/dev/null || true
    pkill -f "airflow standalone" 2>/dev/null || true
    pkill -f "airflow api-server" 2>/dev/null || true
fi

if lsof -ti:8000 >/dev/null 2>&1; then
    echo "Остановка Backend на порту 8000..."
    pkill -f "python.*main.py" 2>/dev/null || true
    pkill -f "uvicorn.*8000" 2>/dev/null || true
fi

if lsof -ti:8501 >/dev/null 2>&1; then
    echo "Остановка Frontend на порту 8501..."
    pkill -f "streamlit.*8501" 2>/dev/null || true
fi

echo ""

if command -v datahub >/dev/null 2>&1; then
    echo "Остановка DataHub..."
    datahub docker quickstart --stop 2>/dev/null || true
fi

if [ -f "$PROJECT_ROOT/.datahub.pid" ]; then
    DATAHUB_PID=$(cat "$PROJECT_ROOT/.datahub.pid")
    if ps -p "$DATAHUB_PID" > /dev/null 2>&1; then
        echo "Остановка процесса DataHub CLI (PID: $DATAHUB_PID)..."
        kill "$DATAHUB_PID" 2>/dev/null || true
        rm "$PROJECT_ROOT/.datahub.pid"
    fi
fi

if command -v docker >/dev/null 2>&1; then
    if docker ps --format '{{.Names}}' | grep -q '^iceberg-rest$'; then
        echo "Остановка Docker контейнера iceberg-rest..."
        docker stop iceberg-rest >/dev/null 2>&1 || true
    fi
    if docker ps --format '{{.Names}}' | grep -q '^starrocks-allin1$'; then
        echo "Остановка Docker контейнера StarRocks (starrocks-allin1)..."
        docker stop starrocks-allin1 >/dev/null 2>&1 || true
    fi
    if [ -f "$PROJECT_ROOT/monitor/docker-compose.yml" ]; then
        echo "Остановка Monitoring stack (Prometheus/Grafana)..."
        if docker compose version >/dev/null 2>&1; then
            docker compose -f "$PROJECT_ROOT/monitor/docker-compose.yml" down >/dev/null 2>&1 || true
        elif command -v docker-compose >/dev/null 2>&1; then
            docker-compose -f "$PROJECT_ROOT/monitor/docker-compose.yml" down >/dev/null 2>&1 || true
        fi
    fi
fi

echo ""
echo "✅ Остановка сервисов завершена"