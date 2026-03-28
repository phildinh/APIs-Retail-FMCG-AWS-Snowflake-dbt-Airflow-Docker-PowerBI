# ingestion

The ingestion layer is responsible for extracting raw data from
FakeStoreAPI and landing it in AWS S3 as partitioned JSON files.
This is the Bronze layer of the medallion architecture.
```
FakeStoreAPI → Python ingestion → AWS S3 (raw/partitioned JSON)
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
core/utils.py    → UTC timestamps and S3 key formatting
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
and S3, and writing extracted data to S3 as partitioned JSON.
```
storage/db.py    → Snowflake connection + cached S3 client
storage/load.py  → writes JSON to S3 with Hive partitioning
```

Read storage/README.md for full details.

### Step 4 — pipeline.py
Read this last. This is the entry point that connects everything.
Calls extract_all() to pull data from all three endpoints, then
loops through results and loads each entity to S3.

---

## Folder structure
```
ingestion/
├── pipeline.py          ← entry point, run this
├── __init__.py
│
├── core/                ← shared foundations
│   ├── config.py
│   ├── logger.py
│   ├── utils.py
│   └── README.md
│
├── api/                 ← data extraction
│   ├── api_client.py
│   ├── extract.py
│   └── README.md
│
└── storage/             ← data persistence
    ├── db.py
    ├── load.py
    └── README.md
```

---

## Data flow
```
pipeline.py
    │
    ├── FakeStoreExtractor.extract_all()
    │       │
    │       ├── APIClient.get("products")  → 20 records
    │       ├── APIClient.get("users")     → 10 records
    │       └── APIClient.get("carts")     →  7 records
    │
    └── load_to_s3(entity, data)
            │
            ├── products → s3://bucket/raw/products/year=.../month=.../day=.../
            ├── users    → s3://bucket/raw/users/year=.../month=.../day=.../
            └── carts    → s3://bucket/raw/carts/year=.../month=.../day=.../
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
2026-03-28 12:00:02 [INFO] ingestion.pipeline: Pipeline started — run date: 2026-03-28
2026-03-28 12:00:04 [INFO] ingestion.api.api_client: Received 20 records from products
2026-03-28 12:00:04 [INFO] ingestion.api.api_client: Received 10 records from users
2026-03-28 12:00:05 [INFO] ingestion.api.api_client: Received 7 records from carts
2026-03-28 12:00:05 [INFO] ingestion.api.extract: Full extraction complete — 37 total records
2026-03-28 12:00:06 [INFO] ingestion.storage.load: Successfully loaded to s3://bucket/raw/products/...
2026-03-28 12:00:06 [INFO] ingestion.storage.load: Successfully loaded to s3://bucket/raw/users/...
2026-03-28 12:00:06 [INFO] ingestion.storage.load: Successfully loaded to s3://bucket/raw/carts/...
2026-03-28 12:00:06 [INFO] ingestion.pipeline: Pipeline complete — summary:
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
| `SNOWFLAKE_*` | Snowflake connection (used by db.py) |
| `LOG_LEVEL` | INFO in dev, DEBUG for troubleshooting |