from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import yaml
import requests
import os

router = APIRouter()

CONTRACTS_DIR = Path(__file__).parent.parent.parent / "contracts"

AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://localhost:8080")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")


def reload_airflow_dags():
    try:
        session = requests.Session()
        session.auth = (AIRFLOW_USER, AIRFLOW_PASSWORD)
        session.get(f"{AIRFLOW_URL}/api/v2/dags?limit=1", timeout=3)
    except Exception:
        pass


class ContractRequest(BaseModel):
    name: str
    contract: dict


@router.get("")
async def list_contracts():
    contracts = []
    for f in CONTRACTS_DIR.glob("*.yaml"):
        data = yaml.safe_load(f.read_text())
        contracts.append({
            "name": f.stem,
            "version": data.get("version", "unknown"),
            "dataset": data.get("dataset", {}),
            "target": data.get("target", {})
        })
    return contracts


@router.get("/{name}")
async def get_contract(name: str):
    path = CONTRACTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Contract not found")
    return yaml.safe_load(path.read_text())


@router.post("")
async def create_contract(request: ContractRequest):
    path = CONTRACTS_DIR / f"{request.name}.yaml"
    if path.exists():
        raise HTTPException(status_code=400, detail="Contract already exists")
    path.write_text(yaml.dump(request.contract, default_flow_style=False, sort_keys=False))
    reload_airflow_dags()
    return {"status": "created", "name": request.name}


@router.put("/{name}")
async def update_contract(name: str, contract: dict):
    path = CONTRACTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Contract not found")
    path.write_text(yaml.dump(contract, default_flow_style=False, sort_keys=False))
    reload_airflow_dags()
    return {"status": "updated", "name": name}


@router.delete("/{name}")
async def delete_contract(name: str):
    path = CONTRACTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Contract not found")
    path.unlink()
    reload_airflow_dags()
    return {"status": "deleted", "name": name}