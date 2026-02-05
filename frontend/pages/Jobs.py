import os
import streamlit as st
from services.api_client import APIClient

def show():
    st.header("🚀 Запуски и мониторинг Airflow")

    col_refresh, col_status = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Обновить", use_container_width=True):
            st.rerun()

    runs = APIClient.list_runs()
    dags = runs.get("dags", [])

    if not dags:
        st.info("📭 Нет найденных DAG. Убедитесь что:")
        st.markdown("""
        1. **Airflow запущен** и доступен
        2. **Контракты созданы** в папке `contracts/`
        3. **DAG генератор** запущен (файл `dag_generator.py`)
        """)
        return

    dags = sorted(dags, key=lambda d: d["id"])

    if "pending_trigger_dag_id" not in st.session_state:
        st.session_state["pending_trigger_dag_id"] = None

    for dag in dags:
        dag_id = dag["id"]
        is_paused = dag.get("is_paused", False)

        with st.expander(f"{'⏸️' if is_paused else '▶️'} {dag_id}", expanded=True):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown("**Статус:**")
                if is_paused:
                    st.warning("⏸️ На паузе")
                else:
                    st.success("▶️ Активен")

            with col2:
                st.markdown("**Действия:**")
                if st.button("▶️ Запустить", key=f"run_{dag_id}", disabled=is_paused):
                    st.session_state["pending_trigger_dag_id"] = dag_id
                    st.rerun()

            with col3:
                st.markdown("**Полезные ссылки:**")
                airflow_url = os.getenv("AIRFLOW_UI_URL", "http://localhost:8070")
                st.markdown(f"[📖 Airflow UI]({airflow_url}/dags/{dag_id})")

            with col4:
                st.markdown("**Контракт:**")
                contract_name = dag_id.replace("contract_", "")
                st.code(f"contracts/{contract_name}.yaml", language="yaml")

    pending = st.session_state.get("pending_trigger_dag_id")
    if pending:
        st.session_state["pending_trigger_dag_id"] = None
        result = APIClient.trigger_dag(pending)
        if result.get("status") == "triggered":
            st.success(f"✅ DAG **{pending}** запущен!")
        else:
            st.error(f"❌ Ошибка запуска **{pending}**: {result.get('message', 'неизвестная ошибка')}")
        st.rerun()
