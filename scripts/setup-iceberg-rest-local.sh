#!/bin/bash

set -e

echo "=== Остановка старого контейнера ==="
docker stop iceberg-rest 2>/dev/null || true
docker rm iceberg-rest 2>/dev/null || true

echo "=== Очистка warehouse ==="
WAREHOUSE_PATH="/home/fushimori/projects/lakehouse-data-platform/data/warehouse"
rm -rf "$WAREHOUSE_PATH"/*
mkdir -p "$WAREHOUSE_PATH"

echo "=== Запуск нового контейнера ==="
docker run -d \
  --name iceberg-rest \
  -p 8181:8181 \
  -v "$WAREHOUSE_PATH:/warehouse" \
  -e CATALOG_WAREHOUSE=/warehouse \
  -e CATALOG_IO__IMPL=org.apache.iceberg.hadoop.HadoopFileIO \
  -e CATALOG_CATALOG__IMPL=org.apache.iceberg.hadoop.HadoopCatalog \
  -e CATALOG_WRITE__FORMAT__DEFAULT=parquet \
  tabulario/iceberg-rest:latest

echo "=== Ожидание запуска (5 сек) ==="
sleep 5

echo "=== Проверка ==="
echo "1. Контейнер запущен:"
docker ps | grep iceberg-rest

echo ""
echo "2. REST-сервер отвечает:"
curl -s http://localhost:8181/ 2>/dev/null && echo "✓ OK" || echo "✗ Не отвечает"

echo ""
echo "3. Конфигурация warehouse:"
curl -s -X GET "http://localhost:8181/v1/config" | jq '.["catalog.config"].warehouse' 2>/dev/null || echo "Не удалось получить"

echo ""
echo "=========================================="
echo "Готово! REST Catalog запущен."
echo "Warehouse: $WAREHOUSE_PATH"
echo "URL: http://localhost:8181"
echo "=========================================="
