import streamlit as st
import yaml
from services.api_client import APIClient

def build_contract_form(contract_data=None, contract_name=None):
    is_edit = contract_data is not None
    
    if contract_data:
        dataset = contract_data.get("dataset", {})
        schema = contract_data.get("schema", {})
        quality = contract_data.get("quality", {})
        target = contract_data.get("target", {})
        partitioning = target.get("partitioning", [])
        orchestration = contract_data.get("orchestration", {})
        
        default_name = contract_name if contract_name else dataset.get("name", "")
        default_version = contract_data.get("version", "2.0.0")
        default_domain = dataset.get("domain", "reddit")
        default_zone = dataset.get("zone", "raw")
        default_format = dataset.get("format", "json")
        default_location = dataset.get("location", "")
        default_multiline = dataset.get("multiline", True)
        default_schema = yaml.dump(schema, default_flow_style=False) if schema else ""
        default_not_null = "\n".join(quality.get("not_null", []))
        default_target_zone = target.get("zone", "curated")
        default_target_format = target.get("format", "iceberg")
        default_catalog = target.get("catalog", "rest")
        default_database = target.get("database", "")
        default_table = target.get("table", "")
        default_write_mode = target.get("write_mode", "upsert")
        default_primary_key = target.get("primary_key", "")
        default_partition_field = partitioning[0].get("field", "") if partitioning else ""
        default_partition_transform = partitioning[0].get("transform", "day") if partitioning else "day"
        default_schedule = orchestration.get("schedule", "0 1 * * *")
    else:
        default_name = ""
        default_version = "2.0.0"
        default_domain = "reddit"
        default_zone = "raw"
        default_format = "json"
        default_location = ""
        default_multiline = True
        default_schema = '{\n  "comment_id": "data.id",\n  "post_id": "data.link_id",\n  "body": "data.body"\n}'
        default_not_null = "comment_id\npost_id\ncreated_utc"
        default_target_zone = "curated"
        default_target_format = "iceberg"
        default_catalog = "rest"
        default_database = "reddit"
        default_table = "comments"
        default_write_mode = "upsert"
        default_primary_key = "comment_id"
        default_partition_field = "created_ts"
        default_partition_transform = "day"
        default_schedule = "0 1 * * *"
    
    st.subheader("Метаданные")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Имя контракта *", value=default_name, disabled=is_edit, help="Уникальное имя контракта")
        version = st.text_input("Версия", value=default_version)
    with col2:
        dataset_name = st.text_input("Имя датасета *", value=default_name, help="Название dataset в Lakehouse")
        dataset_domain = st.text_input("Домен", value=default_domain, help="Домен данных (reddit, sales, etc.)")

    st.divider()
    st.subheader("Dataset (источник)")
    col1, col2, col3 = st.columns(3)
    with col1:
        zone = st.selectbox("Зона", ["raw", "curated", "trusted"], index=["raw", "curated", "trusted"].index(default_zone) if default_zone in ["raw", "curated", "trusted"] else 0, help="Зона хранения источника")
        format_src = st.selectbox("Формат", ["json", "csv", "parquet", "iceberg"], index=["json", "csv", "parquet", "iceberg"].index(default_format) if default_format in ["json", "csv", "parquet", "iceberg"] else 0, help="Формат исходного файла")
    with col2:
        location = st.text_input("Путь к файлу *", value=default_location, placeholder="data/sample/comments.json")
        multiline = st.checkbox("Multiline JSON", value=default_multiline, help="JSON с множественными объектами в строках")
    with col3:
        schema_hint = st.text_area("Схема (JSON mapping)", value=default_schema, height=120, help="Маппинг полей источника в целевые")

    st.divider()
    st.subheader("Quality (проверки качества)")
    quality_not_null = st.text_area("Поля NOT NULL", value=default_not_null, help="Поля, которые обязательны к заполнению")

    st.divider()
    st.subheader("Target (цель)")
    col1, col2, col3 = st.columns(3)
    with col1:
        target_zone = st.selectbox("Целевая зона", ["curated", "trusted"], index=["curated", "trusted"].index(default_target_zone) if default_target_zone in ["curated", "trusted"] else 0, help="Зона хранения результата")
        target_format = st.selectbox("Целевой формат", ["iceberg", "delta", "hudi"], index=["iceberg", "delta", "hudi"].index(default_target_format) if default_target_format in ["iceberg", "delta", "hudi"] else 0, disabled=True)
    with col2:
        catalog = st.selectbox("Каталог", ["rest", "glue", "hive"], index=["rest", "glue", "hive"].index(default_catalog) if default_catalog in ["rest", "glue", "hive"] else 0, help="Catalog для Iceberg")
        database = st.text_input("База данных *", value=default_database)
        table_name = st.text_input("Имя таблицы *", value=default_table)
    with col3:
        write_mode = st.selectbox("Режим записи", ["upsert", "overwrite", "append"], index=["upsert", "overwrite", "append"].index(default_write_mode) if default_write_mode in ["upsert", "overwrite", "append"] else 0, help="append=добавить, overwrite=перезаписать, upsert=обновить существующие")
        primary_key = st.text_input("Primary key", value=default_primary_key, help="Поле для уникальной идентификации записей")

    st.divider()
    st.subheader("Partitioning")
    partition_field = st.text_input("Поле партиционирования", value=default_partition_field)
    partition_transform = st.selectbox("Трансформация", ["day", "hour", "month", "year", "none"], index=["day", "hour", "month", "year", "none"].index(default_partition_transform) if default_partition_transform in ["day", "hour", "month", "year", "none"] else 0)

    st.divider()
    st.subheader("Orchestration (DAG)")
    schedule = st.text_input("Cron schedule", value=default_schedule, help="Расписание в формате cron (0 1 * * * = каждый день в 01:00)")

    return {
        "name": name,
        "version": version,
        "dataset_name": dataset_name,
        "dataset_domain": dataset_domain,
        "zone": zone,
        "format_src": format_src,
        "location": location,
        "multiline": multiline,
        "schema_hint": schema_hint,
        "quality_not_null": quality_not_null,
        "target_zone": target_zone,
        "target_format": target_format,
        "catalog": catalog,
        "database": database,
        "table_name": table_name,
        "write_mode": write_mode,
        "primary_key": primary_key,
        "partition_field": partition_field,
        "partition_transform": partition_transform,
        "schedule": schedule
    }

def build_contract_dict(form_data):
    try:
        schema = yaml.safe_load(form_data["schema_hint"]) if form_data["schema_hint"].strip() else {}
    except:
        schema = {}

    quality_fields = [f.strip() for f in form_data["quality_not_null"].split('\n') if f.strip()]

    contract = {
        "version": form_data["version"],
        "dataset": {
            "name": form_data["dataset_name"],
            "domain": form_data["dataset_domain"],
            "zone": form_data["zone"],
            "location": form_data["location"],
            "format": form_data["format_src"],
            "multiline": form_data["multiline"]
        },
        "schema": schema,
        "quality": {
            "not_null": quality_fields
        } if quality_fields else {},
        "target": {
            "zone": form_data["target_zone"],
            "format": form_data["target_format"],
            "catalog": form_data["catalog"],
            "database": form_data["database"],
            "table": form_data["table_name"],
            "write_mode": form_data["write_mode"],
            "primary_key": form_data["primary_key"],
            "partitioning": [
                {"field": form_data["partition_field"], "transform": form_data["partition_transform"]}
            ] if form_data["partition_field"] and form_data["partition_transform"] != "none" else []
        },
        "orchestration": {
            "schedule": form_data["schedule"]
        } if form_data["schedule"] else {}
    }
    return contract

def show():
    st.header("📋 Управление контрактами")

    if "edit_contract" not in st.session_state:
        st.session_state.edit_contract = None

    tab1, tab2, tab3 = st.tabs(["📋 Список контрактов", "➕ Создать контракт", "✏️ Редактировать контракт"])

    with tab1:
        contracts = APIClient.get_contracts()
        if not contracts:
            st.info("Нет созданных контрактов. Создайте первый контракт во вкладке 'Создать контракт'.")
        else:
            for c in contracts:
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    with st.expander(f"{c['name']} (v{c.get('version', 'N/A')})"):
                        st.json(c)
                        st.info("💡 Для запуска контракта перейдите на страницу 'Запуски'")
                with col2:
                    if st.button("✏️ Редактировать", key=f"edit_{c['name']}"):
                        st.session_state.edit_contract = c['name']
                        st.rerun()
                with col3:
                    if st.button("🗑️ Удалить", key=f"delete_{c['name']}"):
                        APIClient.delete_contract(c['name'])
                        st.success(f"Контракт '{c['name']}' удален")
                        st.rerun()

    with tab2:
        with st.form("create_contract_form"):
            form_data = build_contract_form()
            submitted = st.form_submit_button("Создать контракт", type="primary")

            if submitted:
                if not form_data["name"] or not form_data["dataset_name"] or not form_data["location"] or not form_data["table_name"] or not form_data["database"]:
                    st.error("Заполните обязательные поля (*)")
                else:
                    contract = build_contract_dict(form_data)
                    result = APIClient.create_contract(form_data["name"], contract)
                    if result.get("status") == "created":
                        st.success(f"✅ Контракт '{form_data['name']}' создан! DAG будет автоматически создан в Airflow.")
                        st.rerun()
                    else:
                        st.error(f"Ошибка: {result.get('error', 'Неизвестная ошибка')}")

    with tab3:
        contracts = APIClient.get_contracts()
        if not contracts:
            st.info("Нет контрактов для редактирования.")
        else:
            contract_names = [c['name'] for c in contracts]
            selected_contract = st.selectbox("Выберите контракт для редактирования", contract_names, index=contract_names.index(st.session_state.edit_contract) if st.session_state.edit_contract in contract_names else 0)
            
            if selected_contract:
                contract_data = APIClient.get_contract(selected_contract)
                
                with st.form("edit_contract_form"):
                    form_data = build_contract_form(contract_data, selected_contract)
                    submitted = st.form_submit_button("Сохранить изменения", type="primary")

                    if submitted:
                        if not form_data["dataset_name"] or not form_data["location"] or not form_data["table_name"] or not form_data["database"]:
                            st.error("Заполните обязательные поля (*)")
                        else:
                            contract = build_contract_dict(form_data)
                            result = APIClient.update_contract(selected_contract, contract)
                            if result.get("status") == "updated":
                                st.success(f"✅ Контракт '{selected_contract}' обновлен! DAG будет автоматически обновлен в Airflow.")
                                st.session_state.edit_contract = None
                                st.rerun()
                            else:
                                st.error(f"Ошибка: {result.get('error', 'Неизвестная ошибка')}")
