# Retail FMCG Data Pipeline

**Production-grade ELT pipeline · FakeStoreAPI → S3 → Snowflake → dbt → Airflow · Star schema with SCD Type 2**

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Snowflake](https://img.shields.io/badge/Snowflake-Data_Warehouse-teal)
![dbt](https://img.shields.io/badge/dbt-1.7.19-amber)
![Airflow](https://img.shields.io/badge/Airflow-2.8.1-purple)
![AWS](https://img.shields.io/badge/AWS-S3-green)
![Tests](https://img.shields.io/badge/pytest-15_passing-brightgreen)

---

## Overview

An end-to-end retail analytics pipeline built to simulate a production FMCG data engineering workload. Raw transactional data is extracted from a REST API, landed in S3 as Hive-partitioned JSON, loaded into Snowflake via `COPY INTO`, transformed through a dbt medallion architecture (Bronze → Silver → Gold), and served to Power BI via a star schema — all orchestrated by Airflow running in Docker.

---

## Architecture

```
FakeStoreAPI → Python (requests + tenacity) → AWS S3 (Hive-partitioned JSON)
     → Snowflake RAW (COPY INTO specific file) → dbt STAGING (table)
     → dbt Snapshots (SCD Type 2) → dbt MARTS (views) → Power BI
```

| Layer | Location | Strategy | Materialisation |
|---|---|---|---|
| **Bronze** | S3 + Snowflake RAW | Incremental append, never truncate | Raw tables |
| **Silver** | Snowflake STAGING | Rebuilt on each dbt run | Table |
| **Gold** | Snowflake MARTS | Always fresh, no storage cost | View |

---

## Project Status

| Phase | Description | 
|---|---|
| 1 | Environment setup — Python, Snowflake, AWS, dbt | 
| 2 | Ingestion layer — API extract, S3 load, COPY INTO Snowflake | 
| 3 | pytest test suite — 15 tests across extract + load modules | 
| 4 | dbt models — staging, snapshots (SCD Type 2), star schema marts | 
| 5 | Airflow + Docker — 6-task DAG, XCom, containerised orchestration | 
| 6 | CI/CD + README — GitHub Actions pytest on every push | 

---

## Repository Structure

```
ecommerce-pipeline/
├── ingestion/                       # Python ELT package
│   ├── pipeline.py                  # Main entry point — run_pipeline()
│   ├── api/
│   │   ├── api_client.py            # HTTP client with tenacity retry
│   │   └── extract.py               # FakeStoreExtractor class
│   ├── storage/
│   │   ├── db.py                    # Snowflake connection pool + S3 client
│   │   ├── load.py                  # Writes JSON to S3
│   │   └── copy_into_snowflake.py   # COPY INTO specific file per run
│   └── core/
│       ├── config.py                # Pydantic BaseSettings — env vars
│       ├── logger.py                # colorlog setup
│       └── utils.py                 # enrich_records, format_s3_key
│
├── tests/                           # pytest suite — 15 tests
│   ├── conftest.py                  # Shared fixtures
│   ├── test_extract.py              # 6 tests — API extraction
│   └── test_load.py                 # 9 tests — S3 loading (moto)
│
├── dbt/                             # dbt project
│   ├── models/
│   │   ├── staging/                 # stg_products, stg_users, stg_carts
│   │   └── marts/                   # fact_order_items, dim_customer, dim_product, dim_date
│   ├── snapshots/                   # products_snapshot, customers_snapshot (SCD Type 2)
│   ├── seeds/                       # fact_order_items_seed.csv — 50,000 synthetic rows
│   └── macros/                      # generate_schema_name.sql
│
├── dags/
│   └── ecommerce_pipeline_dag.py    # 6-task Airflow DAG with XCom
│
├── snowflake/                       # setup.sql, create_raw_tables.sql
├── scripts/                         # generate_seed_data.py
├── Dockerfile                       # Extends apache/airflow:2.8.1
├── docker-compose.yml               # webserver + scheduler + postgres
├── requirements.txt
└── .github/workflows/
    └── ci.yml                       # pytest on every push
```

---

## Star Schema

**Fact table:** `fact_order_items` — grain: one row per product line item per order

| Table | Type | Key Design |
|---|---|---|
| `fact_order_items` | Fact | Surrogate key via `dbt_utils.generate_surrogate_key` |
| `dim_customer` | SCD Type 2 | Current records: `dbt_valid_to IS NULL` |
| `dim_product` | SCD Type 2 | Tracks price and rating changes over time |
| `dim_date` | Date spine | 730 days from 2024-01-01, `date_key` as YYYYMMDD |
| `fact_order_items_seed` | Seed | 50,000 synthetic rows, UNION ALL'd into the mart |

---

## Airflow DAG

6 tasks run daily in strict sequence:

```
extract_and_load_s3 (Python)
  → copy_to_snowflake (Python · XCom)
  → dbt_snapshot (Bash)
  → dbt_run_staging (Bash)
  → dbt_run_marts (Bash)
  → dbt_test (Bash)
```

`s3_keys` and `run_id` are passed from task 1 to task 2 via XCom. `catchup=False` — no backfill on first run.

---

## Quickstart

**Prerequisites:** Python 3.11, Docker, a Snowflake account, an AWS account with S3 access.

```bash
# 1. Clone and set up environment
git clone https://github.com/phildinh/APIs-Retail-FMCG-AWS-Snowflake-dbt-Airflow-Docker
cd APIs-Retail-FMCG-AWS-Snowflake-dbt-Airflow-Docker
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# Fill in your Snowflake, AWS, and FakeStoreAPI credentials

# 3. Load env vars (PowerShell — run every new session)
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
    }
}

# 4. Run the ingestion pipeline
python -m ingestion.pipeline

# 5. Run dbt
cd dbt
dbt snapshot
dbt run
dbt test

# 6. Run tests
pytest tests/ -v

# 7. Spin up Airflow (Docker)
docker-compose up airflow-init
docker-compose up -d
# Open http://localhost:8080
```

> **Note:** `profiles.yml` is gitignored. Recreate it manually after cloning with your Snowflake credentials. Never commit credentials to the repo.

---

## Environment Variables

| Variable | Description |
|---|---|
| `SNOWFLAKE_ACCOUNT` | Your Snowflake account identifier |
| `SNOWFLAKE_USER` | Your Snowflake username |
| `SNOWFLAKE_PASSWORD` | Your Snowflake password |
| `SNOWFLAKE_WAREHOUSE` | `ECOMMERCE_WH` |
| `SNOWFLAKE_DATABASE` | `ECOMMERCE_DB` |
| `SNOWFLAKE_ROLE` | `TRANSFORMER` |
| `SNOWFLAKE_SCHEMA` | `RAW` |
| `AWS_ACCESS_KEY_ID` | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key |
| `AWS_REGION` | `ap-southeast-2` |
| `AWS_BUCKET_NAME` | Your S3 bucket name |
| `FAKESTORE_BASE_URL` | `https://fakestoreapi.com` |
| `ENVIRONMENT` | `dev` |
| `LOG_LEVEL` | `INFO` (use `DEBUG` for troubleshooting) |

---

## Tech Stack

| Tool | Version | Role |
|---|---|---|
| Python | 3.11.9 | Ingestion pipeline, data enrichment, pytest |
| AWS S3 | — | Bronze layer — Hive-partitioned raw JSON storage |
| Snowflake | — | Data warehouse — RAW, STAGING, MARTS schemas |
| dbt | 1.7.19 | Transformation, SCD Type 2 snapshots, data testing |
| Airflow | 2.8.1 | Orchestration — daily DAG, XCom, task-level retries |
| Docker | — | Containerised Airflow (webserver + scheduler + postgres) |
| Power BI | — | Analytics layer via native Snowflake connector |
| GitHub Actions | — | CI/CD — pytest on every push |

---

## Known Gotchas

- `numpy` must be pinned to `<2` — the Snowflake connector breaks with numpy 2.x
- SCD Type 2 current record filter is `dbt_valid_to IS NULL` — not `dbt_is_current`
- `COPY INTO` targets a specific file path per run — not the whole S3 folder
- RAW tables are incremental and append-only — never truncate them
- dbt seeds land in STAGING by default — override schema in `dbt_project.yml` to route to MARTS
- Load env vars into PowerShell every new session — they don't persist between terminal restarts

---

## Author

**Phil Dinh** · Sydney, Australia  
Data Engineer · FMCG & Retail Analytics background  

