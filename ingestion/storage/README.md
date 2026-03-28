# ingestion/storage

Handles all persistence concerns for the ingestion layer.
Responsible for managing connections, writing raw data to S3,
and copying that data into Snowflake RAW schema.
Nothing in this folder knows about the API or business logic —
it only knows how to store data reliably.

---

## Files

### db.py
Connection management for Snowflake and AWS S3.

Provides two functions used across the ingestion layer:
- `get_snowflake_connection()` — opens a fresh Snowflake connection
- `get_s3_client()` — returns a cached boto3 S3 client

Usage:
    from ingestion.storage.db import get_snowflake_connection, get_s3_client

    # Snowflake — open, use, always close
    conn = get_snowflake_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
    finally:
        conn.close()

    # S3 — cached, just use it
    client = get_s3_client()
    client.put_object(Bucket="my-bucket", Key="path/file.json", Body="...")

---

### load.py
Writes extracted API data to S3 as partitioned JSON files.

Takes a list of records and an entity name, builds the S3 key
using Hive partitioning, serialises to JSON, and uploads.
Returns the S3 key so the caller knows exactly where the file landed.

Usage:
    from ingestion.storage.load import load_to_s3

    s3_key = load_to_s3(entity="products", data=[{...}, {...}])
    # returns: raw/products/year=2026/month=03/day=28/products_20260328_120002.json

---

### copy_into_snowflake.py
Copies JSON files from S3 into Snowflake RAW schema tables.

Provides two functions:
- `build_copy_query(entity, s3_key)` — builds the COPY INTO SQL for a given entity and S3 path
- `copy_raw_to_snowflake(s3_keys, run_id)` — iterates over all entities, executes COPY INTO,
  and returns a dict of `{entity: rows_loaded}`

Supported entities: `products`, `users`, `carts`.

Each entity maps to its RAW table with explicit column-to-JSON-path bindings
using Snowflake's semi-structured `$1:field::TYPE` syntax.
Nested objects (`rating`, `name`, `address`, `products`) are cast to VARIANT.

Usage:
    from ingestion.storage.copy_into_snowflake import copy_raw_to_snowflake

    s3_keys = {
        "products": "raw/products/year=2026/month=03/day=28/products_20260328_120002.json",
        "users":    "raw/users/year=2026/month=03/day=28/users_20260328_120003.json",
        "carts":    "raw/carts/year=2026/month=03/day=28/carts_20260328_120004.json",
    }
    results = copy_raw_to_snowflake(s3_keys=s3_keys, run_id="abc-123")
    # returns: {"products": 20, "users": 10, "carts": 7}

The function reads from the Snowflake external stage `@raw_s3_stage` and
uses the named file format `raw_json_format` — both must exist in Snowflake
before this runs (created by `snowflake/create_raw_tables.sql`).

---

## Design decisions

**Why is `get_snowflake_connection()` not cached?**
A Snowflake connection is a live network socket. Caching it with
`lru_cache` means a dropped connection returns a dead object to
every caller with no way to recover. A fresh connection is opened
each time and the caller is responsible for closing it in a
`try/finally` block.

**Why is `get_s3_client()` cached?**
An S3 client is stateless — it is a configured HTTP client with
no live socket. Safe to create once and reuse across the entire
pipeline run. Caching avoids the overhead of re-initialising
credentials on every call.

**Why does `load_to_s3()` return the S3 key?**
The caller needs to know where the file landed — both for logging
and for passing the path to Snowflake's COPY INTO command later.
Returning the key keeps the function useful without adding
unnecessary coupling between storage and ingestion logic.

**Why does `build_copy_query()` strip the entity prefix from the S3 key?**
The external stage `@raw_s3_stage` is already rooted at the bucket root.
The COPY INTO path must be relative to the stage, so the leading
`raw/{entity}/` prefix is removed, leaving only the partition sub-path
(e.g. `year=2026/month=03/day=28/products_20260328_120002.json`).

**Why `ON_ERROR = 'CONTINUE'`?**
If a single malformed record exists in the file, the pipeline should not
halt and leave all other entities unloaded. CONTINUE skips bad rows and
logs them — the row count returned by COPY INTO reflects only successfully
loaded rows, making failures visible without blocking the run.

**Why LOADER role for Snowflake?**
The ingestion layer only needs write access to the RAW schema.
Connecting as LOADER enforces least privilege at the connection
level — even if something goes wrong, this connection cannot
touch STAGING or MARTS.
