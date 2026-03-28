# ingestion/storage

Handles all persistence concerns for the ingestion layer.
Responsible for managing connections and writing raw data to S3.
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
    # returns: raw/products/year=2024/month=01/day=15/products_20240115_113200.json

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

**Why LOADER role for Snowflake?**
The ingestion layer only needs write access to the RAW schema.
Connecting as LOADER enforces least privilege at the connection
level — even if something goes wrong, this connection cannot
touch STAGING or MARTS.
