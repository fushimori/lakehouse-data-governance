import streamlit as st
import requests

def show():
    st.header("DataHub каталог")

    datahub_url = st.text_input("DataHub URL", "http://localhost:8080")

    if st.button("Загрузить метаданные"):
        result = requests.post(f"{datahub_url}/api/v1")
        st.success("Загрузка запущена")

    st.info("Для просмотра каталога откройте DataHub UI напрямую")