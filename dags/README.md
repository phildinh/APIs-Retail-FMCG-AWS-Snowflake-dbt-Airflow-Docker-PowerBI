# dags

Apache Airflow DAGs for orchestrating the ecommerce pipeline.
Each DAG in this folder is automatically discovered by the Airflow
scheduler when the container starts.

The DAG folder is mounted as a Docker volume so any change you make
to a file here is picked up by Airflow immediately — no rebuild needed.

---

## Files

### ecommerce_pipeline_dag.py
The main pipeline DAG. Runs the full data flow end to end:

```
run_ingestion  >>  dbt_staging  >>  dbt_marts
```

**Schedule:** `@daily` — runs once per day automatically.
**Catchup:** disabled — only runs from today forward, no backfill.
**Retries:** 1 retry per task, 5 minute wait between attempts.

---

## Tasks

### Task 1 — run_ingestion
```
cd /app && python -m ingestion.pipeline
```
Runs the Python ingestion pipeline inside the container.

What it does:
- Extracts products (20), users (10), carts (7) from FakeStoreAPI
- Enriches each record with metadata (`_loaded_at`, `_source`, `_entity`, `_load_date`, `_run_id`)
- Writes partitioned JSON files to S3 (`raw/{entity}/year=.../month=.../day=.../`)
- Executes `COPY INTO` to load all three entities into Snowflake RAW schema

Fails if: API is unreachable, AWS credentials are wrong, or Snowflake connection fails.

---

### Task 2 — dbt_staging
```
cd /app/dbt && dbt run --select staging.*
```
Runs all three staging models against the RAW data loaded in Task 1.

What it does:
- `stg_products` — deduplicates + flattens `rating` VARIANT
- `stg_users`    — deduplicates + flattens `name` and `address` VARIANT
- `stg_carts`    — deduplicates + LATERAL FLATTEN `products` array

Fails if: Task 1 didn't load data, Snowflake connection fails, or a model has a SQL error.

---

### Task 3 — dbt_marts
```
cd /app/dbt && dbt run --select marts.*
```
Runs all four mart models against the staging data from Task 2.

What it does:
- `dim_date`         — generates date spine (no upstream dependency)
- `dim_product`      — SCD2 product dimension from products_snapshot
- `dim_customer`     — SCD2 customer dimension from customers_snapshot
- `fact_order_items` — joins stg_carts + all dims, UNION ALL with seed data

Fails if: Task 2 failed, snapshots are missing, or a model has a SQL error.

---

## Data flow summary

```
FakeStoreAPI
    ↓  [Task 1 — run_ingestion]
S3 raw JSON → Snowflake RAW
    ↓  [Task 2 — dbt_staging]
Snowflake STAGING (stg_products, stg_users, stg_carts)
    ↓  [Task 3 — dbt_marts]
Snowflake MARTS (dim_date, dim_product, dim_customer, fact_order_items)
```

---

## How to run

**Trigger manually from the UI:**
1. Go to `http://localhost:8080`
2. Login: `admin / admin`
3. Find `ecommerce_pipeline` → click the Play button → Trigger DAG

**Trigger from the terminal:**
```bash
docker-compose exec airflow airflow dags trigger ecommerce_pipeline
```

**Check task logs from the terminal:**
```bash
docker-compose exec airflow airflow tasks logs ecommerce_pipeline run_ingestion <run_id>
```

---

## Prerequisites before triggering the DAG

The following must be set up in Snowflake before the DAG runs:

| Prerequisite | Created by |
|---|---|
| `ECOMMERCE_DB` database and schemas | `snowflake/setup.sql` |
| `RAW.PRODUCTS`, `RAW.USERS`, `RAW.CARTS` tables | `snowflake/create_raw_tables.sql` |
| `@raw_s3_stage` external S3 stage | `snowflake/create_raw_tables.sql` |
| `raw_json_format` file format | `snowflake/create_raw_tables.sql` |
| `MARTS.FACT_ORDER_ITEMS_SEED` seed table | `dbt seed` (run once manually) |

---

## Environment variables required

All passed into the container via `env_file: .env` in `docker-compose.yml`:

| Variable | Used by |
|---|---|
| `SNOWFLAKE_*` | ingestion pipeline + dbt profiles.yml |
| `AWS_ACCESS_KEY_ID` | ingestion pipeline (S3 writes) |
| `AWS_SECRET_ACCESS_KEY` | ingestion pipeline (S3 writes) |
| `AWS_REGION` | ingestion pipeline |
| `AWS_BUCKET_NAME` | ingestion pipeline |
| `FAKESTORE_BASE_URL` | ingestion pipeline (API calls) |
| `LOG_LEVEL` | ingestion pipeline logging |

---

## Design decisions

**Why BashOperator instead of PythonOperator?**
BashOperator runs shell commands directly in the container.
This keeps the DAG simple and decoupled — the DAG doesn't need to
import ingestion or dbt libraries. It just runs the same commands
you would run manually, which makes debugging straightforward.

**Why three separate tasks instead of one?**
If `dbt_staging` fails (e.g. a SQL error), Airflow marks only that
task red. You can fix the issue and re-run from that task without
re-running ingestion. Granular tasks mean granular retries.

**Why `catchup=False`?**
The pipeline extracts live data from FakeStoreAPI. Backfilling past
dates would just re-extract today's data multiple times. Catchup is
only useful for pipelines that process historical partitions.

**Why `@daily` schedule?**
FakeStoreAPI is a static test API — it returns the same data every
time. Daily is appropriate for a learning project. In production you
would choose a schedule based on how often the source data updates.
