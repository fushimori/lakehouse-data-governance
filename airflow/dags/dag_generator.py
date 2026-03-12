from pathlib import Path
from datetime import datetime, timedelta
import os
import subprocess
import yaml
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
CONTRACTS_DIR = PROJECT_ROOT / "contracts"


def _run_etl(contract_path: str, **kwargs):
    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(PROJECT_ROOT)
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    env["PATH"] = f"{PROJECT_ROOT / 'venv' / 'bin'}:{env.get('PATH', '')}"
    env.setdefault("DATAHUB_GMS_URL", "http://localhost:8080")
    env.setdefault("DATAHUB_OPENLINEAGE_ENV", "PROD")
    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts" / "run_etl.sh"), contract_path],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"run_etl failed (exit {result.returncode})\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def _run_datahub_ingest(**kwargs):
    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(PROJECT_ROOT)
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    env["PATH"] = f"{PROJECT_ROOT / 'venv' / 'bin'}:{env.get('PATH', '')}"
    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts" / "run_datahub_ingest.sh")],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"run_datahub_ingest failed (exit {result.returncode})\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def create_dag_from_contract(contract_path: Path):
    with open(contract_path) as f:
        contract = yaml.safe_load(f)

    dag_id = f"contract_{contract['dataset']['name']}"
    schedule = contract.get("orchestration", {}).get("schedule", None)
    contract_path_str = str(contract_path.absolute())

    default_args = {
        "owner": "data-governance",
        "depends_on_past": False,
        "start_date": datetime(2024, 1, 1),
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
    }

    dag = DAG(
        dag_id=dag_id,
        schedule=schedule,
        default_args=default_args,
        catchup=False,
        is_paused_upon_creation=False,
        tags=["contract", contract.get("dataset", {}).get("domain", "default")],
    )

    with dag:
        run_etl = PythonOperator(
            task_id="run_etl",
            python_callable=_run_etl,
            op_args=[contract_path_str],
            retries=2,
            retry_delay=timedelta(minutes=2),
        )

        run_datahub_ingest = PythonOperator(
            task_id="run_datahub_ingest",
            python_callable=_run_datahub_ingest,
            retries=2,
            retry_delay=timedelta(minutes=2),
        )

        run_etl >> run_datahub_ingest

    return dag


def generate_all_dags():
    for contract_file in CONTRACTS_DIR.glob("*.yaml"):
        dag = create_dag_from_contract(contract_file)
        globals()[dag.dag_id] = dag


generate_all_dags()
