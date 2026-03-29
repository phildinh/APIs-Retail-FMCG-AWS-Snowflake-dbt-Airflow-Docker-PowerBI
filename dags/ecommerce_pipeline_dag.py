from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="ecommerce_pipeline",
    description="Extract from FakeStoreAPI → S3 → Snowflake RAW → dbt staging → dbt marts",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["ecommerce", "ingestion", "dbt"],
) as dag:

    run_ingestion = BashOperator(
        task_id="run_ingestion",
        bash_command="cd /app && python -m ingestion.pipeline",
    )

    dbt_staging = BashOperator(
        task_id="dbt_staging",
        bash_command="cd /app/dbt && dbt run --select staging.*",
    )

    dbt_marts = BashOperator(
        task_id="dbt_marts",
        bash_command="cd /app/dbt && dbt run --select marts.*",
    )

    run_ingestion >> dbt_staging >> dbt_marts