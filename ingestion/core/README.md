# ingestion/core

Shared utilities used across the entire ingestion layer.
No business logic lives here — only foundational building blocks
that every other module depends on.

---

## Files

### config.py
Centralised configuration using Pydantic `BaseSettings`.

Reads all environment variables from `.env` at startup and exposes
them as a single typed `Settings` object. Any value that might change
between environments (credentials, URLs, log levels) lives here.

Usage:
    from ingestion.core.config import get_settings

    settings = get_settings()
    print(settings.snowflake_account)

Variables loaded:
- Snowflake connection details
- AWS credentials and bucket name
- FakeStoreAPI base URL
- Pipeline environment and log level

---

### logger.py
Centralised logger using Python `logging` and `colorlog`.

Configured once and imported by every module. Log level is driven
by `LOG_LEVEL` in `.env` so you can switch between `DEBUG` and `INFO`
without touching source code.

Output format:
    2024-01-15 11:32:00 [INFO] ingestion.api.extract: Fetching products

Colours by level:
- DEBUG    → cyan
- INFO     → green
- WARNING  → yellow
- ERROR    → red
- CRITICAL → bold red

Usage:
    from ingestion.core.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Starting extraction")

---

### utils.py
Shared helper functions with no external dependencies.

Provides consistent date/time handling and S3 key formatting
used across the ingestion layer. All timestamps are UTC.

Functions:
- `get_utc_now()`  → current datetime in UTC
- `get_run_date()` → today's date as YYYY-MM-DD string
- `format_s3_key(entity, file_format)` → partitioned S3 path
- `enrich_records(entity, data, run_id)` → stamps metadata fields onto every record
  - `_loaded_at`  — UTC timestamp of extraction
  - `_source`     — always "fakestoreapi"
  - `_entity`     — which endpoint the record came from
  - `_load_date`  — date portion of the run
  - `_run_id`     — unique ID tying all records from one run together
  
S3 key format:
    raw/{entity}/year={yyyy}/month={mm}/day={dd}/{entity}_{timestamp}.json

Example:
    raw/products/year=2024/month=01/day=15/products_20240115_113200.json

The year/month/day partition structure follows Hive partitioning
convention, making the data compatible with Athena and Snowflake
external stages for efficient partition pruning.

---

## Design decisions

**Why `@lru_cache` on `get_settings()` and `get_logger()`?**
Both are expensive to initialise — settings reads and parses the `.env`
file, logger builds and configures a handler. Caching ensures each is
created exactly once and reused across the entire pipeline run.

**Why UTC everywhere?**
Pipelines run across time zones. Using local time produces inconsistent
results depending on where the code runs. UTC is always the same
everywhere.

**Why no business logic in core?**
Keeping core purely foundational means any module can import from it
without creating circular dependencies. Business logic belongs in
`api/` or `storage/`.