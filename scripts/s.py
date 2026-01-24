from pyiceberg.catalog import load_catalog

# В PyIceberg нет HadoopCatalog (это только в Java версии)
# Для локальной файловой системы используем SqlCatalog с SQLite
# Это эквивалент HadoopCatalog для Python
warehouse_path = "/home/fushimori/projects/lakehouse-data-platform/data/warehouse"
catalog = load_catalog(
    "local",
    type="sql",
    uri=f"sqlite:///{warehouse_path}/pyiceberg_catalog.db",
    warehouse=f"file://{warehouse_path}"
)

# Создаем namespace если не существует
try:
    catalog.create_namespace("reddit")
except Exception:
    pass  # Namespace уже существует

# Проверяем таблицы
tables = catalog.list_tables("reddit")
print(f"Tables in 'reddit': {tables}")

# Загружаем таблицу (если существует)
if "reddit.posts" in [f"reddit.{t}" for t in tables]:
    tbl = catalog.load_table("reddit.posts")
    print(f"Schema: {tbl.schema()}")
else:
    print("Table 'reddit.posts' does not exist yet")
