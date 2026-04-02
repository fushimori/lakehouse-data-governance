#!/bin/bash

set +e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "🚀 Запуск всех сервисов платформы"
echo "=========================================="
echo ""

if [ ! -d "venv" ]; then
    echo -e "${RED}✗ Ошибка: venv не найден${NC}"
    echo "Создай виртуальное окружение: python -m venv venv"
    exit 1
fi

source venv/bin/activate

export PROJECT_ROOT="$PROJECT_ROOT"

export AIRFLOW_HOME="${AIRFLOW_HOME:-$PROJECT_ROOT/airflow}"
mkdir -p "$AIRFLOW_HOME"

export AIRFLOW__CORE__DAGS_FOLDER="$AIRFLOW_HOME/dags"
export AIRFLOW__API__PORT=8070
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

check_port() {
    local port=$1
    if lsof -ti:$port >/dev/null 2>&1; then
        return 1
    else
        return 0
    fi
}

wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=${3:-30}
    local attempt=0
    
    echo -n "Ожидание $name..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -fsS "$url" >/dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    echo -e " ${YELLOW}⚠ (таймаут)${NC}"
    return 1
}

compose_up_file() {
    local file_path="$1"
    if docker compose version >/dev/null 2>&1; then
        docker compose -f "$file_path" up -d
        return $?
    fi
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose -f "$file_path" up -d
        return $?
    fi
    return 1
}

echo "1️⃣  Запуск Iceberg REST..."
if ! command -v docker >/dev/null 2>&1; then
    echo -e "   ${RED}✗ Ошибка: Docker не установлен${NC}"
else
    if docker ps --format '{{.Names}}' | grep -q "^iceberg-rest$"; then
        echo -e "   ${YELLOW}⚠ Контейнер iceberg-rest уже запущен${NC}"
    elif docker ps -a --format '{{.Names}}' | grep -q "^iceberg-rest$"; then
        echo "   Найден существующий контейнер iceberg-rest (stopped), запускаю..."
        docker start iceberg-rest >/dev/null 2>&1 || true
        echo -e "   ${GREEN}✓ Iceberg REST запущен на http://localhost:8181${NC}"
    else
        bash scripts/setup-iceberg-rest-local.sh >/dev/null 2>&1
        echo -e "   ${GREEN}✓ Iceberg REST запущен на http://localhost:8181${NC}"
    fi
fi
echo ""

echo "2️⃣  Запуск DataHub..."
if check_port 8080; then
    if command -v datahub >/dev/null 2>&1; then
        echo "   Запускаю DataHub (datahub docker quickstart)..."
        datahub docker quickstart > "$PROJECT_ROOT/datahub.log" 2>&1 &
        DATAHUB_PID=$!
        echo "   PID: $DATAHUB_PID"
        sleep 10
        wait_for_service "http://localhost:8080/health" "DataHub GMS" 90
        echo -e "   ${GREEN}✓ DataHub запущен${NC}"
        echo "   UI: http://localhost:9002 (datahub/datahub)"
        [ -n "$DATAHUB_PID" ] && echo "$DATAHUB_PID" > "$PROJECT_ROOT/.datahub.pid" 2>/dev/null || true
    else
        echo -e "   ${YELLOW}⚠ datahub CLI не найден. Запусти вручную: datahub docker quickstart${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠ DataHub уже запущен (порт 8080)${NC}"
fi
echo ""

echo "3️⃣  Запуск Monitoring (Prometheus + Grafana)..."
if ! command -v docker >/dev/null 2>&1; then
    echo -e "   ${RED}✗ Ошибка: Docker не установлен — мониторинг не будет запущен${NC}"
else
    MONITOR_COMPOSE_FILE="$PROJECT_ROOT/monitor/docker-compose.yml"
    if [ -f "$MONITOR_COMPOSE_FILE" ]; then
        compose_up_file "$MONITOR_COMPOSE_FILE" >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "   ${GREEN}✓ Prometheus и Grafana запущены${NC}"
        else
            echo -e "   ${YELLOW}⚠ Не удалось запустить docker compose для monitor${NC}"
        fi
    else
        echo -e "   ${YELLOW}⚠ Файл monitor/docker-compose.yml не найден${NC}"
    fi
fi

if [ -f "$PROJECT_ROOT/.metrics_exporter.pid" ] && ps -p "$(cat "$PROJECT_ROOT/.metrics_exporter.pid" 2>/dev/null)" >/dev/null 2>&1; then
    echo -e "   ${YELLOW}⚠ Metrics exporter уже запущен${NC}"
else
    echo "   Запускаю metrics exporter на :9108..."
    python "$PROJECT_ROOT/monitor/metrics_exporter.py" > "$PROJECT_ROOT/monitor/metrics_exporter.log" 2>&1 &
    METRICS_EXPORTER_PID=$!
    echo "$METRICS_EXPORTER_PID" > "$PROJECT_ROOT/.metrics_exporter.pid" 2>/dev/null || true
    wait_for_service "http://localhost:9108/metrics" "Metrics exporter" 20
fi
echo ""

echo "4️⃣  Запуск StarRocks (all-in-one)..."
if ! command -v docker >/dev/null 2>&1; then
    echo -e "   ${RED}✗ Ошибка: Docker не установлен — StarRocks не будет запущен${NC}"
else
    PROJECT_WAREHOUSE_PATH="$PROJECT_ROOT/data/warehouse"
    HOST_WAREHOUSE_PATH="/warehouse"
    mkdir -p "$PROJECT_WAREHOUSE_PATH"
    if [ -d "$HOST_WAREHOUSE_PATH" ]; then
        STARROCKS_WAREHOUSE_MOUNT="$HOST_WAREHOUSE_PATH"
    else
        STARROCKS_WAREHOUSE_MOUNT="$PROJECT_WAREHOUSE_PATH"
    fi
    if docker ps --format '{{.Names}}' | grep -q '^starrocks-allin1$'; then
        echo -e "   ${YELLOW}⚠ Контейнер starrocks-allin1 уже запущен${NC}"
    elif docker ps -a --format '{{.Names}}' | grep -q '^starrocks-allin1$'; then
        echo "   Найден существующий контейнер starrocks-allin1 (stopped), запускаю..."
        docker start starrocks-allin1 >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "   ${GREEN}✓ StarRocks контейнер запущен${NC}"
            echo "   SQL (MySQL протокол): 127.0.0.1:9030, user: root"
            echo "   HTTP API:             http://127.0.0.1:8030"
        else
            echo -e "   ${YELLOW}⚠ Не удалось запустить существующий контейнер, пересоздаю...${NC}"
            docker rm -f starrocks-allin1 >/dev/null 2>&1 || true
            docker run -d \
              --name starrocks-allin1 \
              -p 9030:9030 -p 8030:8030 -p 8040:8040 \
              --add-host=host.docker.internal:host-gateway \
              -v "$STARROCKS_WAREHOUSE_MOUNT:/warehouse" \
              starrocks/allin1-ubuntu >/dev/null 2>&1
            if [ $? -eq 0 ]; then
                echo -e "   ${GREEN}✓ StarRocks пересоздан и запущен${NC}"
                echo "   SQL (MySQL протокол): 127.0.0.1:9030, user: root"
                echo "   HTTP API:             http://127.0.0.1:8030"
                echo "   Warehouse mount:      $STARROCKS_WAREHOUSE_MOUNT -> /warehouse"
            else
                echo -e "   ${YELLOW}⚠ Не удалось пересоздать контейнер starrocks-allin1${NC}"
            fi
        fi
    else
        echo "   Запускаю StarRocks all-in-one (FE+BE)..."
        docker run -d \
          --name starrocks-allin1 \
          -p 9030:9030 -p 8030:8030 -p 8040:8040 \
          --add-host=host.docker.internal:host-gateway \
          -v "$STARROCKS_WAREHOUSE_MOUNT:/warehouse" \
          starrocks/allin1-ubuntu >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "   ${GREEN}✓ StarRocks запущен (FE+BE all-in-one)${NC}"
            echo "   SQL (MySQL протокол): 127.0.0.1:9030, user: root"
            echo "   HTTP API:             http://127.0.0.1:8030"
            echo "   Warehouse mount:      $STARROCKS_WAREHOUSE_MOUNT -> /warehouse"
        else
            echo -e "   ${YELLOW}⚠ Не удалось запустить контейнер starrocks-allin1${NC}"
        fi
    fi
fi
echo ""

echo "5️⃣  Запуск Airflow..."
if check_port 8070; then
    if ! command -v airflow >/dev/null 2>&1; then
        echo -e "   ${RED}✗ Ошибка: команда 'airflow' не найдена${NC}"
        echo "   Установи: pip install apache-airflow==3.1.6"
    else
        echo "   Запускаю Airflow standalone..."
        airflow standalone > "$AIRFLOW_HOME/standalone.log" 2>&1 &
        AIRFLOW_PID=$!
        echo "   PID: $AIRFLOW_PID"
        sleep 20
        if check_port 8070; then
            echo -e "   ${YELLOW}⚠ Airflow UI еще не запустился, ожидание...${NC}"
            wait_for_service "http://localhost:8070" "Airflow UI" 45
        else
            echo -e "   ${GREEN}✓ Airflow UI работает${NC}"
        fi
        echo -e "   ${GREEN}✓ Airflow запущен${NC}"
        echo "   UI: http://localhost:8070"
        echo "   Пароль: $(cat "$AIRFLOW_HOME/simple_auth_manager_passwords.json.generated" 2>/dev/null | grep -o '"admin": "[^"]*"' | cut -d'"' -f4 || echo 'admin')"
    fi
else
    echo -e "   ${YELLOW}⚠ Airflow уже запущен на порту 8070${NC}"
fi
echo ""

echo "6️⃣  Запуск Backend (FastAPI)..."
if check_port 8000; then
    echo "   Запускаю backend..."
    cd backend
    python main.py > "$PROJECT_ROOT/backend.log" 2>&1 &
    BACKEND_PID=$!
    cd "$PROJECT_ROOT"
    echo "   PID: $BACKEND_PID"
    wait_for_service "http://localhost:8000/api/contracts" "Backend" 15
    echo -e "   ${GREEN}✓ Backend запущен${NC}"
    echo "   API: http://localhost:8000"
    echo "   Docs: http://localhost:8000/docs"
else
    echo -e "   ${YELLOW}⚠ Backend уже запущен на порту 8000${NC}"
fi
echo ""

echo "7️⃣  Запуск Frontend (Streamlit)..."
if check_port 8501; then
    echo "   Запускаю frontend..."
    cd frontend
    streamlit run app.py --server.port 8501 > "$PROJECT_ROOT/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    cd "$PROJECT_ROOT"
    echo "   PID: $FRONTEND_PID"
    wait_for_service "http://localhost:8501" "Frontend" 15
    echo -e "   ${GREEN}✓ Frontend запущен${NC}"
    echo "   UI: http://localhost:8501"
else
    echo -e "   ${YELLOW}⚠ Frontend уже запущен на порту 8501${NC}"
fi
echo ""

[ -n "$AIRFLOW_PID" ] && echo "$AIRFLOW_PID" > "$PROJECT_ROOT/.airflow.pid" 2>/dev/null || true
[ -n "$BACKEND_PID" ] && echo "$BACKEND_PID" > "$PROJECT_ROOT/.backend.pid" 2>/dev/null || true
[ -n "$FRONTEND_PID" ] && echo "$FRONTEND_PID" > "$PROJECT_ROOT/.frontend.pid" 2>/dev/null || true
[ -n "$DATAHUB_PID" ] && echo "$DATAHUB_PID" > "$PROJECT_ROOT/.datahub.pid" 2>/dev/null || true
[ -n "$METRICS_EXPORTER_PID" ] && echo "$METRICS_EXPORTER_PID" > "$PROJECT_ROOT/.metrics_exporter.pid" 2>/dev/null || true

echo "=========================================="
echo -e "${GREEN}✅ Все сервисы запущены!${NC}"
echo "=========================================="
echo ""
echo "📋 Доступные сервисы:"
echo ""
echo "  🌐 Frontend (Streamlit):    http://localhost:8501"
echo "  🔧 Backend API:            http://localhost:8000"
echo "  📚 Backend Docs:           http://localhost:8000/docs"
echo "  ✈️  Airflow UI:             http://localhost:8070"
echo "  📊 DataHub UI:             http://localhost:9002"
echo "  🗄️  Iceberg REST:            http://localhost:8181"
echo "  ⚙️  StarRocks (FE+BE all-in-one): SQL 127.0.0.1:9030, HTTP 127.0.0.1:8030"
echo "  📈 Prometheus:             http://localhost:9090"
echo "  📉 Grafana:                http://localhost:3000 (admin/admin)"
echo "  🧩 Metrics exporter:       http://localhost:9108/metrics"

