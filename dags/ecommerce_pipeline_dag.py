from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
import sys
import os

# ── Tell Python where your ingestion package lives inside the container ──────
# The volume mounts it at /opt/airflow/ingestion
# Without this, `from ingestion.pipeline import ...` would fail with ModuleNotFoundError
sys.path.insert(0, '/opt/airflow')

# ── Default args apply to every task in the DAG ──────────────────────────────
default_args = {
    'owner': 'phil',
    'start_date': datetime(2024, 1, 1),
    'retries': 1,                    # Retry once before marking failed
}

# ── DAG definition ────────────────────────────────────────────────────────────
with DAG(
    dag_id='ecommerce_pipeline',
    default_args=default_args,
    schedule_interval='@daily',      # Run once per day
    catchup=False,                   # Don't backfill missed runs
    tags=['ecommerce', 'fmcg'],
) as dag:

    # ── Task 1: Extract from FakeStoreAPI and load to S3 ─────────────────────
    # Runs your existing pipeline.py logic
    # Pushes s3_keys and run_id to XCom so Task 2 can use them
    def extract_and_load(**context):
        from ingestion.pipeline import run_pipeline
        
        # run_pipeline() returns the s3 keys written and the run_id
        s3_keys, run_id = run_pipeline()
        
        # Push to XCom — stored in Airflow's metadata DB (postgres)
        context['ti'].xcom_push(key='s3_keys', value=s3_keys)
        context['ti'].xcom_push(key='run_id', value=run_id)

    task1 = PythonOperator(
        task_id='extract_and_load_s3',
        python_callable=extract_and_load,
        provide_context=True,        # Gives the function access to `context` (needed for XCom)
    )

    # ── Task 2: COPY from S3 into Snowflake RAW ───────────────────────────────
    # Pulls the s3_keys and run_id that Task 1 pushed
    def copy_to_snowflake(**context):
        from ingestion.storage.copy_into_snowflake import copy_raw_to_snowflake
        
        ti = context['ti']
        s3_keys = ti.xcom_pull(task_ids='extract_and_load_s3', key='s3_keys')
        run_id  = ti.xcom_pull(task_ids='extract_and_load_s3', key='run_id')
        
        copy_raw_to_snowflake(s3_keys, run_id)

    task2 = PythonOperator(
        task_id='copy_to_snowflake',
        python_callable=copy_to_snowflake,
        provide_context=True,
    )

    # ── Tasks 3–6: dbt commands via BashOperator ──────────────────────────────
    # BashOperator runs a shell command inside the container
    # We cd into /opt/airflow/dbt first (where your dbt project lives)
    # env vars (Snowflake creds) are already in the container from .env via docker-compose

    task3 = BashOperator(
        task_id='dbt_snapshot',
        bash_command='cd /opt/airflow/dbt && dbt snapshot',
    )

    task4 = BashOperator(
        task_id='dbt_run_staging',
        bash_command='cd /opt/airflow/dbt && dbt run --select staging',
    )

    task5 = BashOperator(
        task_id='dbt_run_marts',
        bash_command='cd /opt/airflow/dbt && dbt run --select marts',
    )

    task6 = BashOperator(
        task_id='dbt_test',
        bash_command='cd /opt/airflow/dbt && dbt test',
    )

    # ── Wire the tasks together ───────────────────────────────────────────────
    task1 >> task2 >> task3 >> task4 >> task5 >> task6