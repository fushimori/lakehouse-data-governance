import os
import sys
import time
import uuid
from datetime import datetime, timezone

import requests

OUTPUT_NAMESPACE = "iceberg"


def _source_platform(contract: dict) -> str:
    platform = contract.get("dataset", {}).get("platform")
    if platform:
        return platform
    loc = contract.get("dataset", {}).get("location", "") or ""
    if loc.startswith("s3://"):
        return "s3"
    if loc.startswith("gs://") or loc.startswith("gcs://"):
        return "gcs"
    return "file"


def _output_name(contract: dict) -> str:
    target = contract.get("target", {})
    db, table = target.get("database", ""), target.get("table", "")
    return f"{db}.{table}" if db and table else table


def _build_column_lineage(contract: dict, input_namespace: str) -> dict:
    schema = contract.get("schema", {})
    dataset_name = contract["dataset"]["name"]
    fields = {}
    for output_col, source_path in schema.items():
        fields[output_col] = {
            "inputFields": [
                {
                    "namespace": input_namespace,
                    "name": dataset_name,
                    "field": source_path,
                    "transformations": [
                        {"type": "DIRECT", "subtype": "IDENTITY", "description": "", "masking": False}
                    ],
                }
            ]
        }
    ts_col = "created_utc"
    ts_source = schema.get(ts_col) or next((sp for sp in schema.values() if "created_utc" in str(sp)), ts_col)
    if ts_col in schema or any("created_utc" in str(sp) for sp in schema.values()):
        for derived in ["created_ts", "hour", "day", "month", "year"]:
            fields[derived] = {
                "inputFields": [
                    {
                        "namespace": input_namespace,
                        "name": dataset_name,
                        "field": ts_source,
                        "transformations": [
                            {"type": "DIRECT", "subtype": "IDENTITY", "description": "", "masking": False}
                        ],
                    }
                ]
            }
    return fields


def _build_column_lineage_mapping(contract: dict) -> dict:
    """SDK ColumnLineageMapping: {output_col: [input_col], ...}."""
    schema = contract.get("schema", {})
    mapping = {}
    for output_col, source_path in schema.items():
        mapping[output_col] = [source_path]
    ts_col = "created_utc"
    ts_source = schema.get(ts_col) or next((sp for sp in schema.values() if "created_utc" in str(sp)), ts_col)
    if ts_col in schema or any("created_utc" in str(sp) for sp in schema.values()):
        for derived in ["created_ts", "hour", "day", "month", "year"]:
            mapping[derived] = [ts_source]
    return mapping


def emit_openlineage(contract: dict, datahub_url: str | None = None) -> None:
    url = datahub_url or os.getenv("DATAHUB_GMS_URL", "http://localhost:8080")
    dataset_name = contract["dataset"]["name"]
    output_name = _output_name(contract)
    source_platform = _source_platform(contract)

    if os.getenv("OPENLINEAGE_USE_SDK_ONLY", "").lower() in ("true", "1", "yes"):
        _emit_lineage_sdk_fallback(contract, url)
        return

    endpoint = f"{url.rstrip('/')}/openapi/openlineage/api/v1/lineage"
    target = contract["target"]
    catalog = target.get("catalog", "rest")
    db, table = target.get("database", ""), target.get("table", "")

    schema = contract.get("schema", {})
    ts_col = "created_utc"
    has_ts = ts_col in schema or any(ts_col == sp for sp in schema.values())
    output_cols = list(schema.keys())
    if has_ts:
        output_cols = output_cols + ["created_ts", "hour", "day", "month", "year"]
    output_fields = [{"name": col, "type": "string"} for col in output_cols]
    input_fields = [{"name": src, "type": "string"} for src in schema.values()]

    column_lineage = None
    if os.getenv("OPENLINEAGE_COLUMN_LINEAGE", "true").lower() in ("true", "1", "yes"):
        column_lineage = _build_column_lineage(contract, source_platform)
        if not column_lineage:
            column_lineage = None

    event = {
        "eventType": "COMPLETE",
        "eventTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "run": {
            "runId": str(uuid.uuid4()),
            "facets": {
                "processing_engine": {
                    "_producer": "https://github.com/lakehouse-data-platform",
                    "_schemaURL": "https://openlineage.io/spec/facets/1-1-1/ProcessingEngineRunFacet.json",
                    "name": "spark",
                    "version": "3.5",
                }
            },
        },
        "job": {
            "namespace": "lakehouse-etl",
            "name": dataset_name,
        },
        "inputs": [
            {
                "namespace": source_platform,
                "name": dataset_name,
                "facets": {
                    "dataSource": {
                        "_producer": "https://github.com/lakehouse-data-platform",
                        "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DataSourceDatasetFacet.json",
                        "name": source_platform,
                        "uri": contract["dataset"].get("location", ""),
                    },
                    "schema": {
                        "_producer": "https://github.com/lakehouse-data-platform",
                        "_schemaURL": "https://openlineage.io/spec/facets/1-1-1/SchemaDatasetFacet.json",
                        "fields": input_fields,
                    },
                },
            }
        ],
        "outputs": [
            {
                "namespace": OUTPUT_NAMESPACE,
                "name": output_name,
                "facets": {
                    "dataSource": {
                        "_producer": "https://github.com/lakehouse-data-platform",
                        "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DataSourceDatasetFacet.json",
                        "name": OUTPUT_NAMESPACE,
                        "uri": f"{catalog}://{db}.{table}",
                    },
                    "schema": {
                        "_producer": "https://github.com/lakehouse-data-platform",
                        "_schemaURL": "https://openlineage.io/spec/facets/1-1-1/SchemaDatasetFacet.json",
                        "fields": output_fields,
                    },
                },
            }
        ],
        "producer": "https://github.com/lakehouse-data-platform",
    }

    if column_lineage:
        event["outputs"][0]["facets"]["columnLineage"] = {
            "_producer": "https://github.com/lakehouse-data-platform",
            "_schemaURL": "https://openlineage.io/spec/facets/1-2-0/ColumnLineageDatasetFacet.json",
            "fields": column_lineage,
        }

    max_retries = 3
    last_error = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                endpoint,
                json=event,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if resp.ok:
                print(f"OpenLineage OK: {dataset_name} -> {output_name}", flush=True)
                return
            last_error = f"{resp.status_code}: {resp.text[:500] if resp.text else ''}"
            if 400 <= resp.status_code < 500:
                break
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        except requests.RequestException as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    _emit_lineage_sdk_fallback(contract, url)

def _emit_lineage_sdk_fallback(contract: dict, datahub_url: str) -> None:
    """SDK: создаём upstream (со schema), добавляем lineage с column mapping из контракта."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from datahub.sdk import DataHubClient
        from datahub.sdk.entity_client import EntityClient, Dataset
        from datahub.sdk.lineage_client import LineageClient, DatasetUrn

    try:
        env = os.getenv("DATAHUB_OPENLINEAGE_ENV", "PROD")
        dataset_name = contract["dataset"]["name"]
        output_name = _output_name(contract)
        source_platform = _source_platform(contract)

        client = DataHubClient(server=datahub_url)
        entity_client = EntityClient(client)

        schema = contract.get("schema", {})
        source_fields = [(path, "string") for path in schema.values()] if schema else None
        source_ds = Dataset(
            platform=source_platform,
            name=dataset_name,
            env=env,
            display_name=f"{dataset_name} (source)",
            schema=source_fields,
        )
        entity_client.upsert(source_ds)

        cll = _build_column_lineage_mapping(contract)
        lineage_client = LineageClient(client)
        lineage_client.add_lineage(
            upstream=DatasetUrn(platform=source_platform, name=dataset_name, env=env),
            downstream=DatasetUrn(platform="iceberg", name=output_name, env=env),
            column_lineage=cll if cll else "auto_fuzzy",
        )
        print(f"Lineage (SDK): {source_platform}.{dataset_name} -> iceberg.{output_name}", flush=True)
    except Exception as e:
        print(f"Lineage fallback failed: {e}", file=sys.stderr)
