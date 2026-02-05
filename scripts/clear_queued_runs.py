#!/usr/bin/env python3

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

AIRFLOW_HOME = PROJECT_ROOT / "airflow"
os.environ["AIRFLOW_HOME"] = str(AIRFLOW_HOME)
os.environ["AIRFLOW__CORE__DAGS_FOLDER"] = str(AIRFLOW_HOME / "dags")
os.environ["PROJECT_ROOT"] = str(PROJECT_ROOT)

from airflow.models import DagRun, TaskInstance, DagBag
from airflow.utils.session import provide_session


@provide_session
def clear_problematic_runs(session=None):
    dagbag = DagBag(include_examples=False)
    contract_dags = [dag_id for dag_id in dagbag.dags.keys() if dag_id.startswith("contract_")]
    
    if not contract_dags:
        print("Не найдено contract DAG-ов")
        return
    
    print(f"Найдено contract DAG-ов: {len(contract_dags)}")
    print(f"DAG-и: {', '.join(contract_dags)}")
    print()
    
    total_deleted_runs = 0
    total_deleted_tasks = 0
    
    for dag_id in contract_dags:
        problematic_runs = (
            session.query(DagRun)
            .filter(DagRun.dag_id == dag_id)
            .filter(DagRun.state.in_(["queued", "failed"]))
            .all()
        )
        up_for_retry_tasks = (
            session.query(TaskInstance)
            .filter(TaskInstance.dag_id == dag_id)
            .filter(TaskInstance.state == "up_for_retry")
            .all()
        )
        
        if not problematic_runs and not up_for_retry_tasks:
            print(f"✓ {dag_id}: нет проблемных runs или задач")
            continue
        
        if problematic_runs:
            print(f"  {dag_id}: найдено {len(problematic_runs)} проблемных runs")
            for run in problematic_runs:
                print(f"    - {run.run_id} (state: {run.state})")
            deleted = (
                session.query(DagRun)
                .filter(DagRun.dag_id == dag_id)
                .filter(DagRun.state.in_(["queued", "failed"]))
                .delete()
            )
            
            session.commit()
            total_deleted_runs += deleted
            print(f"  ✓ Удалено {deleted} проблемных runs")
        
        if up_for_retry_tasks:
            print(f"  {dag_id}: найдено {len(up_for_retry_tasks)} задач в состоянии up_for_retry")
            for task in up_for_retry_tasks:
                print(f"    - {task.task_id} (run_id: {task.run_id})")
            deleted_tasks = (
                session.query(TaskInstance)
                .filter(TaskInstance.dag_id == dag_id)
                .filter(TaskInstance.state == "up_for_retry")
                .delete()
            )
            
            session.commit()
            total_deleted_tasks += deleted_tasks
            print(f"  ✓ Удалено {deleted_tasks} задач в состоянии up_for_retry")
        
        print()
    
    print(f"=== Готово ===")
    print(f"Всего удалено проблемных runs: {total_deleted_runs}")
    print(f"Всего удалено задач up_for_retry: {total_deleted_tasks}")
    print()
    print("Теперь можно запускать DAG-и заново - они будут выполняться сразу")


if __name__ == "__main__":
    clear_problematic_runs()
