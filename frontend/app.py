import streamlit as st

st.set_page_config(page_title="Data Governance", layout="wide")

st.title("Data Governance Platform")

st.markdown("---")

st.sidebar.title("Меню")
page = st.sidebar.radio("Страница", ["Контракты", "Запуски", "Каталог"])

if page == "Контракты":
    from pages import Contracts
    Contracts.show()
elif page == "Запуски":
    from pages import Jobs
    Jobs.show()
elif page == "Каталог":
    from pages import Catalog
    Catalog.show()