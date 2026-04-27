# Retail FMCG Data Pipeline — AWS · Snowflake · dbt · Airflow · Docker

> A fully automated, production-grade ELT pipeline built end-to-end — extracting retail data from a REST API, landing it in AWS S3, loading into Snowflake, transforming through a dbt medallion architecture, and orchestrated daily by Airflow running in Docker.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Snowflake](https://img.shields.io/badge/Snowflake-Data_Warehouse-29B5E8)
![dbt](https://img.shields.io/badge/dbt-1.7-FF6849)
![Airflow](https://img.shields.io/badge/Airflow-2.8.1-017CEE)
![AWS S3](https://img.shields.io/badge/AWS-S3-FF9900)
![Docker](https://img.shields.io/badge/Docker-Containerised-2496ED)
![Tests](https://img.shields.io/badge/pytest-15_passing-brightgreen)
![CI](https://img.shields.io/badge/CI-GitHub_Actions-181717)

---

## What Makes This Project Different

Anyone can follow a tutorial connecting an API to a database. What this project demonstrates is building the full stack — ingestion, storage, transformation, snapshot history, orchestration, and testing — as separate, decoupled layers where each one can fail and recover independently.

### The external API went offline mid-project — the pipeline didn't change

FakeStoreAPI became unreliable mid-project. Rather than blocking, the extraction layer was decoupled from the external dependency. A local mock (`mock_data.py`) was written to return the exact same data shape as the real API. Zero changes were needed in S3, Snowflake, dbt, or Airflow. That is the value of clean separation of concerns — your pipeline does not care where the data comes from.

### SCD Type 2 validated end to end — not just theory

dbt snapshots track product prices and customer details over time. When a dimension record changes, the old version is closed with `dbt_valid_to` and a new current version is inserted. `fact_order_items` joins against the version that was active at the time of the order — not today's price.

![SCD Type 2 — before and after product version](docs/scd_before_product.png)
![SCD Type 2 — new version created, old version expired](docs/scd_after_product.png)

### Airflow ran all 6 tasks green on the first successful run

A 6-task DAG orchestrates the full pipeline daily: extract → copy to Snowflake → dbt staging → dbt snapshot → dbt marts → dbt test. Tasks 1 and 2 use `PythonOperator` with XCom to pass runtime values. Tasks 3–6 use `BashOperator` to run dbt CLI commands. Each task is independently retryable.

![Airflow DAG — all 6 tasks green](docs/airflow_success.png)

### Real bugs found and fixed before submission

| Bug | How it was found | Fix |
|---|---|---|
| `run_pipeline()` called `copy_raw_to_snowflake` internally AND the DAG called it again | Double copy on every run | Stripped Snowflake copy out of `run_pipeline()` — DAG owns that step via Task 2 |
| `dbt snapshot` ran before staging in the DAG | Snapshots read from `stg_products`/`stg_users` which didn't exist yet | Fixed task order: staging (Task 3) before snapshot (Task 4) |
| `--select staging` in BashOperator | dbt looked for a model literally named "staging" — found nothing | Changed to `--select staging.*` to select the whole folder |
| `airflow users create` flags treated as separate bash commands | YAML `>` scalar preserved newlines — each `--flag` became its own shell command | Moved all flags to one line |
| `airflow` binary not found after `pip install` in `command:` | bash does not re-hash `PATH` mid-session | Moved Airflow install to Dockerfile — binary available from container startup |

### 15 pytest tests — all passing, no real API or AWS calls

A full pytest suite covers extraction and S3 loading. Every test uses mocks (pytest-mock, moto) — no real HTTP requests, no real S3 writes. CI runs all 15 tests on every push.

![GitHub Actions CI — all checks passing](docs/github_ci_success.png)

---

## Table of Contents

- [Business Problem](#business-problem)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Data Pipeline Flow](#data-pipeline-flow)
- [Database Design](#database-design)
- [Data Engineering Patterns](#data-engineering-patterns)
- [Synthetic Dataset](#synthetic-dataset)
- [CI/CD](#cicd)
- [Project Structure](#project-structure)
- [Setup Guide](#setup-guide)
- [Pipeline Execution](#pipeline-execution)
- [Key Learnings](#key-learnings)

---

## Business Problem

A retail FMCG team tracks products, customers, and orders through a REST API.
The data lives in the API — there is no warehouse, no history, no analytics layer.
Stakeholders cannot answer questions like: *what was the price of this product
when this order was placed?* or *how many units did we sell last month by category?*

**The solution:** Build a cloud ELT pipeline that:
- Extracts raw data daily and lands it in AWS S3 as immutable, partitioned files
- Loads it into Snowflake and transforms it into a clean star schema via dbt
- Preserves full SCD Type 2 history for products and customers
- Combines 50,000 rows of synthetic seed data with live API data for realistic volumes
- Runs automatically every day via Airflow in Docker — no manual steps

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker (local / server)                     │
│                                                                     │
│  ┌──────────────┐    ┌──────────────────────────────────────────┐   │
│  │   Airflow    │───▶│           ecommerce_pipeline DAG         │   │
│  │  @daily      │    │                                          │   │
│  └──────────────┘    │  Task 1          Task 2                  │   │
│                      │  extract_and  →  copy_to_              │   │
│                      │  load_s3         snowflake              │   │
│                      │  (Python)        (Python + XCom)       │   │
│                      │      │               │                   │   │
│                      │      ▼               ▼                   │   │
│                      │  ┌────────┐    ┌───────────┐             │   │
│                      │  │  AWS   │    │ Snowflake │             │   │
│                      │  │   S3   │───▶│   RAW     │             │   │
│                      │  │Bronze  │    │  schema   │             │   │
│                      │  └────────┘    └───────────┘             │   │
│                      │                     │                    │   │
│                      │  Task 3             │                    │   │
│                      │  dbt_run_staging ───┘                    │   │
│                      │  (Silver — STAGING schema)               │   │
│                      │         │                                │   │
│                      │  Task 4 │                                │   │
│                      │  dbt_snapshot                            │   │
│                      │  (SCD Type 2 — products + customers)     │   │
│                      │         │                                │   │
│                      │  Task 5 │                                │   │
│                      │  dbt_run_marts                           │   │
│                      │  (Gold — MARTS schema, star schema)      │   │
│                      │         │                                │   │
│                      │  Task 6 │                                │   │
│                      │  dbt_test                                │   │
│                      │  (data quality validation)               │   │
│                      └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

| Layer | Location | Materialisation | Strategy |
|---|---|---|---|
| Bronze | AWS S3 + Snowflake RAW | Raw tables | Incremental append — never truncate |
| Silver | Snowflake STAGING | Table | Rebuilt on each dbt run |
| Gold | Snowflake MARTS | View | Always fresh from latest snapshot + staging |

---

## Tech Stack

| Tool | Version | Role |
|---|---|---|
| Python | 3.11 | Ingestion pipeline, enrichment, testing |
| AWS S3 | — | Bronze layer — Hive-partitioned raw JSON |
| Snowflake | — | Data warehouse — RAW, STAGING, MARTS schemas |
| dbt Core | 1.7 | SQL transformations, SCD Type 2 snapshots, data quality tests |
| dbt-utils | 1.1.1 | `generate_surrogate_key` for stable dimension keys |
| Apache Airflow | 2.8.1 | Daily orchestration — 6-task DAG with XCom |
| Docker | — | Containerised Airflow (webserver + scheduler + postgres) |
| pytest | 7.4 | 15 unit tests — moto for S3 mocking, pytest-mock for API |
| GitHub Actions | — | CI — pytest on every push and pull request |
| tenacity | 8.2 | Exponential backoff retry on API calls |
| Pydantic Settings | 2.1 | Type-safe environment variable loading |

---

## Data Pipeline Flow

### Daily Execution (@daily via Airflow)

```
Task 1 — extract_and_load_s3 (PythonOperator)
    • FakeStoreExtractor pulls from mock_data.py
      (products: 20 records, users: 10 records, carts: 7 records)
    • enrich_records() stamps every record with:
      _loaded_at, _source, _entity, _load_date, _run_id
    • load_to_s3() writes Hive-partitioned JSON to S3:
      s3://bucket/raw/{entity}/year=YYYY/month=MM/day=DD/{entity}_YYYYMMDD_HHMMSS.json
    • Pushes s3_keys and run_id to XCom
    ↓
Task 2 — copy_to_snowflake (PythonOperator)
    • Pulls s3_keys and run_id from XCom
    • Executes COPY INTO for each entity — targets the specific file from this run
    • COPY INTO RAW.PRODUCTS, RAW.USERS, RAW.CARTS
    • ON_ERROR = 'CONTINUE' — bad rows skipped, good rows loaded
    ↓
Task 3 — dbt_run_staging (BashOperator)
    • dbt run --select staging.*
    • stg_products → deduplicates + flattens rating VARIANT
    • stg_users    → deduplicates + flattens name/address VARIANT
    • stg_carts    → deduplicates + LATERAL FLATTEN products array
    ↓
Task 4 — dbt_snapshot (BashOperator)
    • dbt snapshot
    • products_snapshot → detects price, category, rating changes
    • customers_snapshot → detects email, name, address, phone changes
    • New row written on change — old row closed with dbt_valid_to timestamp
    ↓
Task 5 — dbt_run_marts (BashOperator)
    • dbt run --select marts.*
    • dim_date           → 730-day spine, YYYYMMDD date_key
    • dim_product        → full SCD2 history from products_snapshot
    • dim_customer       → full SCD2 history from customers_snapshot
    • fact_order_items   → stg_carts + dims + 50k seed rows UNION ALL
    ↓
Task 6 — dbt_test (BashOperator)
    • dbt test
    • Validates not_null on all source columns
    • Confirms pipeline loaded clean data end to end
```

### On Failure

Any task failure stops the chain. Airflow marks the failed task red.
Fix the issue and rerun from that task — no need to restart from Task 1.

---

## Database Design

### Snowflake — Three Schemas

```
ECOMMERCE_DB
│
├── RAW schema (Bronze — written by ingestion pipeline)
│   ├── PRODUCTS    ← 20 records per run, append-only
│   ├── USERS       ← 10 records per run, append-only
│   └── CARTS       ← 7 records per run, append-only
│
├── STAGING schema (Silver — written by dbt run staging.*)
│   ├── STG_PRODUCTS   ← deduped + rating VARIANT flattened (table)
│   ├── STG_USERS      ← deduped + name/address VARIANT flattened (table)
│   └── STG_CARTS      ← deduped + products array exploded (table)
│
└── MARTS schema (Gold — written by dbt snapshot + dbt run marts.*)
    ├── PRODUCTS_SNAPSHOT      ← SCD Type 2 history table
    ├── CUSTOMERS_SNAPSHOT     ← SCD Type 2 history table
    ├── FACT_ORDER_ITEMS_SEED  ← 50,000 synthetic rows (dbt seed)
    ├── DIM_DATE               ← 730-day spine (view)
    ├── DIM_PRODUCT            ← full SCD2 product history (view)
    ├── DIM_CUSTOMER           ← full SCD2 customer history (view)
    └── FACT_ORDER_ITEMS       ← central fact table (view)
```

### Star Schema (Gold Layer)

```
                  ┌──────────────────┐
                  │    dim_date      │
                  │  date_key (PK)   │
                  │  full_date       │
                  │  day/month/year  │
                  │  quarter         │
                  │  is_weekend      │
                  └────────┬─────────┘
                           │
┌──────────────────┐       │       ┌──────────────────┐
│   dim_product    │       │       │   dim_customer   │
│   (SCD Type 2)   │       │       │   (SCD Type 2)   │
│  product_key(PK) │       │       │ customer_key(PK) │
│  product_id      │       │       │  user_id         │
│  product_name    ├───┐   │   ┌───┤  first/last_name │
│  category        │   │   │   │   │  full_name       │
│  price           │   │   │   │   │  email/phone     │
│  rating_score    │   │   │   │   │  city/street     │
│  effective_from  │   │   │   │   │  effective_from  │
│  effective_to    │   │   │   │   │  effective_to    │
└──────────────────┘   │   │   │   └──────────────────┘
                       │   │   │
                       ▼   ▼   ▼
             ┌──────────────────────────┐
             │     fact_order_items     │
             │  order_item_key  (PK)    │
             │  order_id                │
             │  product_key     (FK)    │
             │  customer_key    (FK)    │
             │  date_key        (FK)    │
             │  product_id              │
             │  user_id                 │
             │  quantity                │
             │  unit_price              │
             │  total_price             │
             │  order_date              │
             │  loaded_at               │
             │  run_id                  │
             └──────────────────────────┘
```

`fact_order_items` combines two sources via `UNION ALL`:
- **pipeline_orders** — live data from stg_carts joined against all three dims
- **seed_orders** — 50,000 synthetic rows from `fact_order_items_seed` joined against dims

---

## Data Engineering Patterns

| Pattern | Implementation | Where |
|---|---|---|
| **Medallion architecture** | Bronze (RAW) → Silver (STAGING) → Gold (MARTS) | Full pipeline |
| **Hive partitioning** | `/year=/month=/day=/` S3 folder structure | S3 / load.py |
| **Metadata enrichment** | `_loaded_at`, `_source`, `_entity`, `_load_date`, `_run_id` on every record | utils.py |
| **Idempotent COPY INTO** | Snowflake tracks loaded files — same file never loaded twice | copy_into_snowflake.py |
| **Deduplication** | `ROW_NUMBER() OVER (PARTITION BY id, _run_id ORDER BY _loaded_at DESC)` | All staging models |
| **LATERAL FLATTEN** | Explodes products VARIANT array — one row per item per cart | stg_carts.sql |
| **SCD Type 2** | dbt snapshots with `strategy='check'` — expire old rows, insert new | products_snapshot, customers_snapshot |
| **Surrogate keys** | `dbt_utils.generate_surrogate_key([natural_key, dbt_valid_from])` | All dimension models |
| **XCom** | `s3_keys` and `run_id` passed between Task 1 and Task 2 | Airflow DAG |
| **Retry logic** | tenacity exponential backoff — 3 attempts, 2s → 10s | api_client.py |
| **Separation of concerns** | core / api / storage — each layer knows nothing about the others | ingestion package |
| **Data quality tests** | `not_null` on all source columns via `sources.yml` | dbt test |
| **UNION ALL for seed** | Synthetic + live data combined at the mart layer | fact_order_items.sql |

---

## Synthetic Dataset

Generated using `scripts/generate_seed_data.py` with `random.seed(42)` for reproducible results.

### Dataset Size

| Source | Records | How used |
|---|---|---|
| FakeStoreAPI mock — products | 20 | Extracted per pipeline run |
| FakeStoreAPI mock — users | 10 | Extracted per pipeline run |
| FakeStoreAPI mock — carts | 7 | Extracted per pipeline run |
| Seed — fact_order_items_seed | 50,000 | Loaded once, UNION ALL into fact table |

### Seed Data Details

50,000 order item rows generated with seasonal weighting:

| Month | Relative Weight | Reason |
|---|---|---|
| December | 2.0x | Peak holiday shopping |
| November | 1.5x | Pre-Christmas |
| January | 1.4x | Post-Christmas sales |
| July / August | 1.1x | Mid-year sales |
| February / March / April | 0.8–0.9x | Quieter retail months |

Price per product matches exact FakeStoreAPI product prices ($7.95 – $695.00).
Orders contain 1–4 products each. Quantity ranges from 1–5 units per line item.

---

## CI/CD

GitHub Actions runs checks on every push to any branch.

### CI — every push and pull request

| Job | What it checks |
|---|---|
| **Run pytest** | All 15 tests across `test_extract.py` and `test_load.py` |

![GitHub Actions CI — all checks passing](docs/github_ci_success.png)

Tests use mocking throughout — no real API calls, no real S3 writes, no Snowflake connection needed in CI.

---

## Project Structure

```
APIs-Retail-FMCG-AWS-Snowflake-dbt-Airflow-Docker/
│
├── ingestion/                         ← Python ELT package (Bronze layer)
│   ├── pipeline.py                    ← Entry point — run_pipeline() → (s3_keys, run_id)
│   ├── mock_data.py                   ← Local mock replacing FakeStoreAPI
│   ├── core/
│   │   ├── config.py                  ← Pydantic BaseSettings — reads from .env
│   │   ├── logger.py                  ← colorlog setup — colour-coded by level
│   │   └── utils.py                   ← enrich_records, format_s3_key, get_run_date
│   ├── api/
│   │   ├── api_client.py              ← Generic HTTP client with tenacity retry
│   │   └── extract.py                 ← FakeStoreExtractor — products, users, carts
│   └── storage/
│       ├── db.py                      ← get_snowflake_connection, get_s3_client
│       ├── load.py                    ← Writes enriched JSON to S3
│       └── copy_into_snowflake.py     ← COPY INTO RAW tables from S3 stage
│
├── tests/                             ← pytest suite — 15 tests, all mocked
│   ├── conftest.py                    ← Shared fixtures (mock API, mock S3, mock settings)
│   ├── test_extract.py                ← 6 tests — FakeStoreExtractor
│   └── test_load.py                   ← 9 tests — load_to_s3 (moto)
│
├── dbt/                               ← dbt project (Silver + Gold layers)
│   ├── dbt_project.yml                ← Project config — staging TABLE, marts VIEW
│   ├── profiles.yml                   ← Snowflake connection via env vars (gitignored)
│   ├── packages.yml                   ← dbt_utils 1.1.1
│   ├── models/
│   │   ├── staging/
│   │   │   ├── sources.yml            ← RAW source declarations + not_null tests
│   │   │   ├── stg_products.sql       ← Dedup + flatten rating VARIANT
│   │   │   ├── stg_users.sql          ← Dedup + flatten name/address VARIANT
│   │   │   └── stg_carts.sql          ← Dedup + LATERAL FLATTEN products array
│   │   └── marts/
│   │       ├── dim_date.sql           ← 730-day generated spine
│   │       ├── dim_product.sql        ← Full SCD2 history from products_snapshot
│   │       ├── dim_customer.sql       ← Full SCD2 history from customers_snapshot
│   │       └── fact_order_items.sql   ← Joins all dims + UNION ALL seed
│   ├── snapshots/
│   │   ├── products_snapshot.sql      ← strategy=check on price/category/rating
│   │   └── customers_snapshot.sql     ← strategy=check on email/name/address/phone
│   └── seeds/
│       └── fact_order_items_seed.csv  ← 50,000 synthetic order rows
│
├── dags/
│   └── ecommerce_pipeline_dag.py      ← 6-task Airflow DAG with XCom
│
├── snowflake/                         ← One-time Snowflake setup scripts
│   ├── setup.sql                      ← Warehouse, database, schemas, roles
│   └── create_raw_tables.sql          ← RAW tables, S3 stage, file format
│
├── scripts/
│   └── generate_seed_data.py          ← Generates fact_order_items_seed.csv
│
├── docs/                              ← Screenshots for README
├── Dockerfile                         ← Extends apache/airflow:2.8.1
├── docker-compose.yml                 ← webserver + scheduler + postgres
├── requirements.txt                   ← Python dependencies
└── .github/workflows/
    └── ci.yml                         ← pytest on every push
```

---

## Setup Guide

### Prerequisites

- Python 3.11
- Docker Desktop
- Snowflake account
- AWS account with S3 access
- Git

### 1. Clone and Set Up Environment

```bash
git clone https://github.com/phildinh/APIs-Retail-FMCG-AWS-Snowflake-dbt-Airflow-Docker
cd APIs-Retail-FMCG-AWS-Snowflake-dbt-Airflow-Docker
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configure Credentials

```bash
cp .env.example .env
# Fill in your Snowflake and AWS credentials
```

### 3. Load Environment Variables — PowerShell

```powershell
# Run every new terminal session
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
    }
}
```

### 4. Set Up Snowflake (run once)

Run these SQL scripts in Snowflake Worksheets in order:
```
snowflake/setup.sql              → creates warehouse, database, schemas, roles
snowflake/create_raw_tables.sql  → creates RAW tables, S3 stage, file format
```

### 5. Set Up dbt

```bash
cd dbt
dbt deps           # install dbt_utils package
dbt debug          # verify Snowflake connection
dbt seed           # load fact_order_items_seed.csv to MARTS schema (run once)
cd ..
```

### 6. Run the Pipeline Manually

```bash
# Full pipeline — extract + S3 + Snowflake RAW
python -m ingestion.pipeline

# dbt transformations — in correct order
cd dbt
dbt run --select staging.*
dbt snapshot
dbt run --select marts.*
dbt test
```

### 7. Run Tests

```bash
pytest tests/ -v
```

### 8. Spin Up Airflow in Docker

```bash
# First time — initialise DB and create admin user
docker-compose up airflow-init

# Start all services
docker-compose up -d

# Open Airflow UI
# http://localhost:8080  —  login: admin / admin
```

---

## Pipeline Execution

### Trigger from Airflow UI

1. Go to `http://localhost:8080`
2. Login: `admin / admin`
3. Find `ecommerce_pipeline` → toggle it on → click the Play button → Trigger DAG

### Trigger from Terminal

```bash
docker-compose exec airflow-webserver airflow dags trigger ecommerce_pipeline
```

### Check Task Logs

```bash
docker-compose logs airflow-scheduler -f
```

Or click any task in the Airflow UI → **Logs**.

### Expected Row Counts After a Successful Run

| Table | Expected Rows | Notes |
|---|---|---|
| `RAW.PRODUCTS` | 20 per run | Append-only — grows each run |
| `RAW.USERS` | 10 per run | Append-only |
| `RAW.CARTS` | 7 per run | Append-only |
| `STAGING.STG_PRODUCTS` | 20 | Deduped — rebuilt each run |
| `STAGING.STG_CARTS` | ~14 | Exploded cart items |
| `MARTS.FACT_ORDER_ITEMS` | 50,000+ | Seed rows + pipeline rows |

---

## Key Learnings

**Why decouple the extraction layer from the external API?**
FakeStoreAPI went offline mid-project. Because `FakeStoreExtractor` reads from
`mock_data.py` with the same interface as the real API, the rest of the pipeline
required zero changes. Decoupling source from logic is not just good practice —
it is what lets you keep working when things outside your control break.

**Why separate `run_pipeline()` from `copy_raw_to_snowflake()`?**
The Airflow DAG treats extract-to-S3 and copy-to-Snowflake as two separate tasks
so each can fail and retry independently. If Snowflake is temporarily unreachable,
you do not need to re-extract from the API. `run_pipeline()` returns `(s3_keys, run_id)`
so the DAG can pass them via XCom to the next task.

**Why `strategy='check'` for dbt snapshots?**
FakeStoreAPI does not return an `updated_at` timestamp — so `strategy='timestamp'`
is not available. The `check` strategy compares specific column values on every run
and writes a new snapshot row only when something actually changed. The trade-off
is a full column scan on every `dbt snapshot` execution.

**Why keep ALL versions in dim_product and dim_customer?**
Removing `WHERE dbt_valid_to IS NULL` keeps every historical version in the dimension.
This allows `fact_order_items` to join against the product price that was current at
the time of the order — not today's price. Without full history, every historical
fact row would silently show the wrong price.

**Why UNION ALL seed data into the fact table instead of loading it through the pipeline?**
The API returns only 7 carts — not enough to demonstrate realistic analytics.
50,000 synthetic rows are unioned in at the mart layer to simulate real FMCG volumes.
`UNION ALL` is correct here because both sources share the same grain (one row per
product per order) but have no shared key to join on.

**Why are RAW tables append-only?**
The RAW schema is an immutable audit log of what the API returned on each run.
Deduplication happens in staging — never in RAW. This means you can always
replay history and trace exactly what data arrived and when.

**Why task ordering matters — staging before snapshot?**
`products_snapshot` and `customers_snapshot` both read from `stg_products` and
`stg_users`. If snapshot runs before staging, it reads stale data from the previous
run. The correct order is: `copy_to_snowflake → dbt_run_staging → dbt_snapshot → dbt_run_marts`.

---

## Author

**Phil Dinh**
Data Engineer · Sydney, Australia

- GitHub: [github.com/phildinh](https://github.com/phildinh)
- LinkedIn: [linkedin.com/in/phil-dinh](https://www.linkedin.com/in/phil-dinh/)

---

## License

MIT License — feel free to use this project as a reference for your own data engineering work.
