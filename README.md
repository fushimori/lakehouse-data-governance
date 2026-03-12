# Lakehouse Data Platform

## Sample version

### 1. Установка зависимостей

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Генерация тестовых данных (для ETL)

```bash
python scripts/json_dump_gen.py
```

Создаёт `data/sample/posts.json` и `data/sample/comments.json`

### 3. Запуск всех сервисов

```bash
bash scripts/start_all.sh
```

Запускает: Iceberg REST, DataHub, Airflow, Backend, Frontend.

**Остановка:**
```bash
bash scripts/stop_all.sh
```

### 4. Проверка

| Сервис | URL |
|--------|-----|
| **Frontend (Streamlit)** | http://localhost:8501 |
| **Backend API** | http://localhost:8000 |
| **Backend Docs** | http://localhost:8000/docs |
| **Airflow UI** | http://localhost:8070 |
| **DataHub UI** | http://localhost:9002 (datahub/datahub) |
| **Iceberg REST** | http://localhost:8181 |

## Как работают DAG'и

1. Создай контракт в `contracts/*.yaml` или в Streamlit (Contracts)
2. Airflow автоматически создаст DAG (до 30 секунд)
3. DAG появится в Airflow UI
4. Запусти через Streamlit (Jobs) или вручную в Airflow UI
5. DAG выполняет: `run_etl` (Spark ETL + OpenLineage) → `run_datahub_ingest` (синхронизация Iceberg с DataHub). Lineage эмитится из ETL в DataHub через OpenLineage API.

