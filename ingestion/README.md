# ingestion

The ingestion layer is responsible for extracting raw data from
FakeStoreAPI, landing it in AWS S3 as partitioned JSON files,
and copying it into Snowflake RAW schema.
This is the Bronze layer of the medallion architecture.
```
FakeStoreAPI → Python ingestion → AWS S3 (raw/partitioned JSON) → Snowflake RAW
```

---

## How to read this layer

The ingestion layer is split into three subfolders, each with a
single responsibility. Read them in this order to understand how
everything connects before looking at pipeline.py.

### Step 1 — core/
Start here. These are the shared foundations everything else depends on.
No business logic, no API calls, no storage. Just config, logging,
and utilities.
```
core/config.py   → loads all environment variables via Pydantic
core/logger.py   → configures colour-coded logging used everywhere
core/utils.py    → UTC timestamps, S3 key formatting, metadata enrichment
```

Read core/README.md for full details.

### Step 2 — api/
Read this second. This is where data comes from.
Handles all outbound HTTP concerns — making requests to FakeStoreAPI,
retrying on network failures, and returning clean Python dictionaries.
```
api/api_client.py  → generic HTTP client with tenacity retry logic
api/extract.py     → business-specific extractor for each endpoint
```

Read api/README.md for full details.

### Step 3 — storage/
Read this third. This is where data goes.
Handles all persistence concerns — managing connections to Snowflake
and S3, writing extracted data to S3, and copying it into Snowflake.
```
storage/db.py                   → Snowflake connection + cached S3 client
storage/load.py                 → writes JSON to S3 with Hive partitioning
storage/copy_into_snowflake.py  → COPY INTO Snowflake RAW from S3 stage
```

Read storage/README.md for full details.

### Step 4 — pipeline.py
Read this last. This is the entry point that connects everything.
Generates a `run_id`, calls `extract_all()` to pull data from all three
endpoints, enriches records with metadata, loads each entity to S3,
then copies all entities from S3 into Snowflake RAW.

---

## Folder structure
```
ingestion/
├── pipeline.py                  ← entry point, run this
├── __init__.py
│
├── core/                        ← shared foundations
│   ├── config.py
│   ├── logger.py
│   ├── utils.py
│   └── README.md
│
├── api/                         ← data extraction
│   ├── api_client.py
│   ├── extract.py
│   └── README.md
│
└── storage/                     ← data persistence
    ├── db.py
    ├── load.py
    ├── copy_into_snowflake.py
    └── README.md
```

---

## Data flow
```
pipeline.py
    │
    ├── 1. Extract
    │   └── FakeStoreExtractor.extract_all()
    │           ├── APIClient.get("products")  → 20 records
    │           ├── APIClient.get("users")     → 10 records
    │           └── APIClient.get("carts")     →  7 records
    │
    ├── 2. Enrich & Load to S3
    │   └── enrich_records() + load_to_s3()
    │           ├── products → s3://bucket/raw/products/year=.../month=.../day=.../
    │           ├── users    → s3://bucket/raw/users/year=.../month=.../day=.../
    │           └── carts    → s3://bucket/raw/carts/year=.../month=.../day=.../
    │
    └── 3. Copy to Snowflake RAW
        └── copy_raw_to_snowflake(s3_keys)
                ├── COPY INTO RAW.PRODUCTS  → 20 rows
                ├── COPY INTO RAW.USERS     → 10 rows
                └── COPY INTO RAW.CARTS     →  7 rows
```

---

## How to run

Make sure your virtual environment is active and `.env` is filled in.
```powershell
# activate venv
.\venv\Scripts\activate

# load environment variables into PowerShell session
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
    }
}

# run the pipeline
python -m ingestion.pipeline
```

Expected output:
```
2026-03-28 12:00:02 [INFO] ingestion.pipeline: Pipeline started — run_id: <uuid> run_date: 2026-03-28
2026-03-28 12:00:04 [INFO] ingestion.api.api_client: Received 20 records from products
2026-03-28 12:00:04 [INFO] ingestion.api.api_client: Received 10 records from users
2026-03-28 12:00:05 [INFO] ingestion.api.api_client: Received 7 records from carts
2026-03-28 12:00:05 [INFO] ingestion.api.extract: Full extraction complete — 37 total records
2026-03-28 12:00:06 [INFO] ingestion.pipeline: products landed at raw/products/year=2026/month=03/day=28/...
2026-03-28 12:00:06 [INFO] ingestion.pipeline: users landed at raw/users/year=2026/month=03/day=28/...
2026-03-28 12:00:06 [INFO] ingestion.pipeline: carts landed at raw/carts/year=2026/month=03/day=28/...
2026-03-28 12:00:06 [INFO] ingestion.pipeline: S3 loading complete — summary:
2026-03-28 12:00:07 [INFO] ingestion.storage.copy_into_snowflake: Starting COPY INTO Snowflake RAW schema
2026-03-28 12:00:08 [INFO] ingestion.storage.copy_into_snowflake: products: 20 rows loaded
2026-03-28 12:00:08 [INFO] ingestion.storage.copy_into_snowflake: users: 10 rows loaded
2026-03-28 12:00:09 [INFO] ingestion.storage.copy_into_snowflake: carts: 7 rows loaded
2026-03-28 12:00:09 [INFO] ingestion.pipeline: Pipeline complete — rows loaded to Snowflake:
2026-03-28 12:00:09 [INFO] ingestion.pipeline:   products: 20 rows
2026-03-28 12:00:09 [INFO] ingestion.pipeline:   users: 10 rows
2026-03-28 12:00:09 [INFO] ingestion.pipeline:   carts: 7 rows
```

---

## S3 output structure

Files land in S3 with Hive partitioning by date:
```
s3://your-bucket/
└── raw/
    ├── products/
    │   └── year=2026/month=03/day=28/
    │           products_20260328_120002.json
    ├── users/
    │   └── year=2026/month=03/day=28/
    │           users_20260328_120004.json
    └── carts/
        └── year=2026/month=03/day=28/
                carts_20260328_120005.json
```

The year/month/day partition structure follows Hive partitioning
convention, making files compatible with Athena and Snowflake
external stages for efficient partition pruning.

---

## Snowflake prerequisites

Before running the pipeline, the following must exist in Snowflake
(created by `snowflake/create_raw_tables.sql`):
- External stage: `@raw_s3_stage` pointing to your S3 bucket
- File format: `raw_json_format` (JSON, strip outer array)
- Tables: `RAW.PRODUCTS`, `RAW.USERS`, `RAW.CARTS`

---

## Environment variables required

All variables are defined in `.env`. See `.env.example` for the
full list. Key variables for this layer:

| Variable | Purpose |
|---|---|
| `FAKESTORE_BASE_URL` | FakeStoreAPI base URL |
| `AWS_ACCESS_KEY_ID` | AWS authentication |
| `AWS_SECRET_ACCESS_KEY` | AWS authentication |
| `AWS_REGION` | S3 bucket region |
| `AWS_BUCKET_NAME` | Target S3 bucket |
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier |
| `SNOWFLAKE_USER` | Snowflake username |
| `SNOWFLAKE_PASSWORD` | Snowflake password |
| `SNOWFLAKE_WAREHOUSE` | Compute warehouse |
| `SNOWFLAKE_DATABASE` | Target database (ECOMMERCE_DB) |
| `SNOWFLAKE_ROLE` | Role used for COPY INTO (LOADER or SYSADMIN) |
| `SNOWFLAKE_SCHEMA` | Default schema (RAW) |
| `LOG_LEVEL` | INFO in dev, DEBUG for troubleshooting |
