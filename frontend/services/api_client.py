import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")


def safe_json(response):
    try:
        return response.json()
    except:
        return {"error": "API unavailable"}


class APIClient:
    @staticmethod
    def get_contracts():
        return safe_json(requests.get(f"{API_URL}/api/contracts"))

    @staticmethod
    def get_contract(name):
        return safe_json(requests.get(f"{API_URL}/api/contracts/{name}"))

    @staticmethod
    def create_contract(name, contract):
        return safe_json(requests.post(f"{API_URL}/api/contracts", json={"name": name, "contract": contract}))

    @staticmethod
    def update_contract(name, contract):
        return safe_json(requests.put(f"{API_URL}/api/contracts/{name}", json=contract))

    @staticmethod
    def delete_contract(name):
        return safe_json(requests.delete(f"{API_URL}/api/contracts/{name}"))

    @staticmethod
    def list_runs():
        return safe_json(requests.get(f"{API_URL}/api/jobs/runs"))

    @staticmethod
    def trigger_dag(dag_id):
        return safe_json(requests.post(f"{API_URL}/api/jobs/trigger/{dag_id}"))

    @staticmethod
    def get_status(dag_id):
        return safe_json(requests.get(f"{API_URL}/api/jobs/status/{dag_id}"))