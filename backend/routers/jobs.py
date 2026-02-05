from fastapi import APIRouter
import os
import subprocess
from pathlib import Path

from airflow.models.dagbag import DagBag

router = APIRouter()

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_AIRFLOW_HOME = PROJECT_ROOT / "airflow"
AIRFLOW_HOME = Path(os.getenv("AIRFLOW_HOME", DEFAULT_AIRFLOW_HOME))
DAGS_FOLDER = Path(
    os.getenv("AIRFLOW__CORE__DAGS_FOLDER", str(AIRFLOW_HOME / "dags"))
)


def _make_airflow_env() -> dict:
    env = os.environ.copy()
    env.setdefault("PROJECT_ROOT", str(PROJECT_ROOT))
    env.setdefault("AIRFLOW_HOME", str(AIRFLOW_HOME))
    env.setdefault("AIRFLOW__CORE__DAGS_FOLDER", str(DAGS_FOLDER))
    return env


@router.get("/runs")
async def list_runs():
    try:
        dagbag = DagBag(
            dag_folder=str(DAGS_FOLDER),
            include_examples=False,
        )
        dags = []
        for dag_id, dag in dagbag.dags.items():
            if not dag_id.startswith("contract_"):
                continue
            dags.append(
                {
                    "id": dag_id,
                    "is_paused": getattr(dag, "is_paused", False),
                }
            )
        dags.sort(key=lambda d: d["id"])
        return {"dags": dags}
    except Exception:
        return {"dags": []}


@router.post("/trigger/{dag_id}")
async def trigger_dag(dag_id: str):
    try:
        env = _make_airflow_env()
        unpause_result = subprocess.run(
            ["airflow", "dags", "unpause", dag_id],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        result = subprocess.run(
            ["airflow", "dags", "trigger", dag_id],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return {
                "status": "error",
                "message": result.stderr or result.stdout,
            }
        return {"status": "triggered", "dag_id": dag_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/status/{dag_id}")
async def get_dag_status(dag_id: str):
    return {"status": "not_implemented"}


@router.post("/reload-dags")
async def reload_dags():
    return {"status": "noop"}