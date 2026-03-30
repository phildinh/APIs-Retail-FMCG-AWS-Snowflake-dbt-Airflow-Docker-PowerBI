# Retail FMCG Data Pipeline
### AWS · Snowflake · dbt · Airflow · Docker · Power BI

---

## Overview

This project is a production-grade end-to-end data pipeline built for the retail and FMCG industry. It demonstrates the full modern data stack — from API ingestion through cloud storage, warehouse transformation, orchestration, and business intelligence reporting.

The pipeline extracts retail product, customer, and order data from a RESTful API, lands it in AWS S3 as partitioned JSON files, loads it incrementally into Snowflake, transforms it through a medallion architecture using dbt, and serves a star schema to Power BI for executive-level reporting.

Every design decision in this project reflects real-world data engineering practice — incremental loading strategies, SCD Type 2 history tracking, idempotent pipeline runs, centralised configuration, structured logging, automated testing, and CI/CD. This is not a tutorial project. It is built the way a junior-to-mid data engineer would build it on the job.

---

## Business Context

Retail and FMCG businesses generate continuous transactional data across products, customers, and orders. Making that data useful for business decisions requires more than just collecting it — it requires a reliable, repeatable process that cleans, models, and delivers it to analysts in a form they can trust.

This pipeline answers real business questions:

- Which products generate the most revenue?
- How does sales performance trend month over month?
- Which customers are our highest-value buyers?
- How have product prices changed over time?
- What does our seasonal demand pattern look like?

These are the questions that drive inventory decisions, pricing strategy, and marketing investment in any retail or FMCG business.

---

## Architecture

The pipeline follows a medallion architecture with three distinct layers, each with a single responsibility.
```
FakeStoreAPI
     │
     │  Python (requests + tenacity)
     ▼
AWS S3 — Bronze Layer
     │  Raw JSON, Hive-partitioned by date
     │  raw/{entity}/year={y}/month={m}/day={d}/{entity}_{timestamp}.json
     │
     │  Snowflake COPY INTO (incremental, file-specific)
     ▼
Snowflake RAW Schema — Bronze Layer
     │  Typed tables with metadata columns
     │  (_loaded_at, _source, _entity, _load_date, _run_id)
     │
     │  dbt staging models
     ▼
Snowflake STAGING Schema — Silver Layer
     │  Cleaned, typed, deduplicated, VARIANT fields flattened
     │  stg_products, stg_users, stg_carts
     │
     │  dbt snapshots + mart models
     ▼
Snowflake MARTS Schema — Gold Layer
     │  Star schema, analytics-ready
     │  fact_order_items, dim_product, dim_customer, dim_date
     │
     │  Power BI connector
     ▼
Power BI Dashboard
     Revenue trends, product performance, customer analysis
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Ingestion | Python 3.11 | API extraction and S3 loading |
| HTTP client | requests + tenacity | Reliable API calls with retry logic |
| Cloud storage | AWS S3 | Raw data lake, Hive-partitioned |
| Data warehouse | Snowflake | Scalable cloud warehouse |
| Transformation | dbt 1.7 | Medallion architecture, testing, documentation |
| Orchestration | Apache Airflow 2.8 | Scheduled pipeline runs |
| Containerisation | Docker + Docker Compose | Reproducible local Airflow environment |
| CI/CD | GitHub Actions | Automated testing on every push |
| BI reporting | Power BI | Executive dashboards on star schema |
| Configuration | Pydantic BaseSettings | Typed, environment-based config |
| Testing | pytest + moto | Ingestion layer unit tests |

---

## Key Engineering Decisions

### Incremental loading at every layer
Each pipeline run extracts fresh data from the API, lands exactly one new file per entity in S3, and loads only that file into Snowflake using `FILES = ('{filename}')` in the COPY INTO command. The RAW tables accumulate data over time and are never truncated. Every record carries a `_run_id` so any pipeline run can be traced end to end.

### SCD Type 2 for slowly changing dimensions
Product prices and customer details change over time. Rather than overwriting historical records, dbt snapshots track every version of each product and customer. When a price changes, the old record is closed with a `dbt_valid_to` timestamp and a new record is opened. The fact table can join to whichever version was current at the time of each order.

### Medallion architecture with clear layer separation
Bronze holds raw data exactly as the API returned it — no transforms, no cleaning. Silver cleans and types the data, flattens nested JSON structures, and deduplicates across pipeline runs. Gold shapes the data into a star schema optimised for analytical queries. Each layer is independently queryable and independently testable.

### Centralised configuration and logging
All credentials and environment-specific settings live in `.env` and are loaded once via Pydantic `BaseSettings`. Every module imports a single logger configured from `LOG_LEVEL` in `.env`. Changing log verbosity or credentials requires editing one file, not hunting through source code.

### Separation of concerns across the ingestion layer
The ingestion layer is split into three subfolders — `api/` for outbound HTTP concerns, `storage/` for persistence concerns, and `core/` for shared utilities. No folder imports from another at the same level. This makes each component independently testable and independently replaceable.

---

## Data Model

The star schema in the MARTS layer is designed around a single business process — order line items.
```
                    ┌─────────────┐
                    │  dim_date   │
                    │  date_key   │
                    └──────┬──────┘
                           │
┌──────────────┐    ┌──────┴──────────┐    ┌──────────────┐
│ dim_customer │    │ fact_order_items │    │ dim_product  │
│ customer_key ├────┤  order_item_key  ├────┤ product_key  │
│ user_id      │    │  customer_key    │    │ product_id   │
│ full_name    │    │  product_key     │    │ product_name │
│ email        │    │  date_key        │    │ category     │
│ city         │    │  quantity        │    │ price        │
│ effective_from│   │  unit_price      │    │ rating_score │
│ effective_to │    │  total_price     │    │ effective_from│
└──────────────┘    │  order_date      │    │ effective_to │
                    │  data_source     │    └──────────────┘
                    └─────────────────┘
```

**Fact table grain:** one row per product line item per order.

**Fact table sources:** real cart data from FakeStoreAPI unioned with 50,000 rows of synthetic order data spanning January 2024 to December 2025. The `data_source` column distinguishes real from synthetic records.

**Dimension history:** `dim_product` and `dim_customer` are built from dbt snapshots. Both carry `effective_from` and `effective_to` columns. Current records have `dbt_valid_to IS NULL`.

---

## Project Structure
```
ecommerce-pipeline/
├── ingestion/               ← Python ingestion layer
│   ├── pipeline.py          ← main entry point
│   ├── api/
│   │   ├── api_client.py    ← HTTP client with tenacity retry
│   │   └── extract.py       ← FakeStoreAPI extractor
│   ├── storage/
│   │   ├── db.py            ← Snowflake connection + S3 client
│   │   ├── load.py          ← writes JSON to S3
│   │   └── copy_into_snowflake.py ← incremental COPY INTO
│   └── core/
│       ├── config.py        ← Pydantic BaseSettings
│       ├── logger.py        ← centralised colorlog
│       └── utils.py         ← enrich_records, format_s3_key
├── tests/                   ← pytest test suite
│   ├── conftest.py          ← shared fixtures
│   ├── test_extract.py      ← 6 tests
│   └── test_load.py         ← 9 tests
├── dbt/                     ← dbt project
│   ├── models/
│   │   ├── staging/         ← Silver layer (tables)
│   │   └── marts/           ← Gold layer (views)
│   ├── snapshots/           ← SCD Type 2
│   ├── seeds/               ← synthetic order data
│   └── macros/              ← generate_schema_name
├── dags/                    ← Airflow DAG
├── snowflake/               ← setup SQL scripts
├── scripts/                 ← utility scripts
├── docs/                    ← architecture diagram
├── docker-compose.yml       ← Airflow services
├── Dockerfile               ← custom Airflow image
└── .github/workflows/       ← CI/CD
    └── ci.yml
```

---

## How to Run

### Prerequisites
- Python 3.11+
- Docker Desktop
- Snowflake account
- AWS account with S3 bucket

### Setup
```powershell
# clone the repo
git clone https://github.com/phildinh/APIs-Retail-FMCG-AWS-Snowflake-dbt-Airflow-Docker.git
cd APIs-Retail-FMCG-AWS-Snowflake-dbt-Airflow-Docker

# create virtual environment
python -m venv venv
.\venv\Scripts\activate

# install dependencies
pip install -r requirements.txt
pip install dbt-snowflake==1.7.2

# configure environment
Copy-Item .env.example .env
# fill in your Snowflake and AWS credentials in .env

# run Snowflake setup (once only)
# open snowflake/setup.sql and snowflake/create_raw_tables.sql
# run both in your Snowflake worksheet
```

### Run the pipeline manually
```powershell
# load env vars
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
    }
}

# run ingestion
python -m ingestion.pipeline

# run dbt
cd dbt
dbt snapshot
dbt run
dbt test
```

### Run tests
```powershell
pytest tests/ -v
```

### Run with Airflow
```powershell
docker-compose up -d
```

Navigate to `http://localhost:8080`, enable the `ecommerce_pipeline` DAG and trigger a run.

---

## What I Learned

This project pushed me to think beyond "does the code run" and into "how does this behave in production." The most valuable lessons were around incremental loading — understanding why `FORCE = TRUE` is a crutch, why file-specific COPY INTO is the right pattern, and why idempotency matters when pipelines run on a schedule.

Working through SCD Type 2 with dbt snapshots gave me a concrete understanding of why dimension history matters for accurate reporting. A fact table that joins to the current product price does not tell you what the price was at order time. That distinction is what separates a real data warehouse from a spreadsheet.

Building each layer with a single responsibility — Python for ingestion, dbt for transformation, Airflow for orchestration — made debugging significantly easier. When something broke, I knew exactly which layer to look at.

---

## Author

**Phil Dinh**
Data Engineer | Sydney, Australia
Transitioning from 5+ years in FMCG/retail analytics into data engineering.

[GitHub](https://github.com/phildinh) · [LinkedIn](https://linkedin.com/in/phildinh)
