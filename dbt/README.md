# dbt

The dbt layer is responsible for transforming raw data that has already
been loaded into Snowflake by the ingestion pipeline.
This covers the Silver and Gold layers of the medallion architecture.
```
Snowflake RAW  →  dbt staging (Silver)  →  dbt marts (Gold)
```

dbt does not move data — it only transforms data already inside Snowflake
by executing SQL SELECT statements and materialising the results as tables or views.

---

## How to read this layer

Read the configuration files first to understand how dbt connects to
Snowflake and where models land. Then read the models in layer order.

### Step 1 — dbt_project.yml + profiles.yml
Start here. These two files tell dbt everything about the project.

- `dbt_project.yml` — project name, which folders contain models/seeds/macros,
  and where each model folder materialises (staging → TABLE, marts → VIEW)
- `profiles.yml` — Snowflake connection details loaded from environment variables

### Step 2 — models/staging/
Read this second. This is the Silver layer.
Takes raw data from `ECOMMERCE_DB.RAW` and cleans it:
deduplicates records, renames columns, and flattens nested VARIANT fields
into typed scalar columns.
```
staging/sources.yml     → declares the RAW tables as dbt sources + data quality tests
staging/stg_products.sql → cleaned product catalogue, rating VARIANT flattened
staging/stg_users.sql    → cleaned users, name/address VARIANT fields flattened
staging/stg_carts.sql    → cleaned carts, products array exploded (one row per item)
```

### Step 3 — snapshots/
Read this third. This is where SCD Type 2 history is captured.
Snapshots sit between staging and marts — they read from staging models
and record a new row every time a tracked column changes.
```
snapshots/products_snapshot.sql  → tracks price, category, rating changes over time
snapshots/customers_snapshot.sql → tracks email, name, address, phone changes over time
```

### Step 4 — models/marts/
Read this fourth. This is the Gold layer.
Takes snapshots and staging models and builds business-ready dimension
and fact tables optimised for reporting and analytics.
```
marts/dim_date.sql         → standalone date spine, no upstream dependencies
marts/dim_product.sql      → full SCD2 product history from products_snapshot
marts/dim_customer.sql     → full SCD2 customer history from customers_snapshot
marts/fact_order_items.sql → central fact table joining all four above models
```

### Step 4 — seeds/
Static CSV data committed to the repo and loaded directly into Snowflake.
Used to supplement the pipeline data in the mart layer — `fact_order_items`
unions seed rows together with live pipeline rows so both sources appear
in one table.
```
seeds/fact_order_items_seed.csv → pre-built order items data, unioned into fact_order_items
```

---

## Folder structure
```
dbt/
├── dbt_project.yml          ← project config (materialisation, paths)
├── profiles.yml             ← Snowflake connection (reads from .env)
├── packages.yml             ← dbt package dependencies
│
├── models/
│   ├── staging/             ← Silver layer: clean + flatten RAW data
│   │   ├── sources.yml      ← source declarations + data quality tests
│   │   ├── stg_products.sql
│   │   ├── stg_users.sql
│   │   └── stg_carts.sql
│   │
│   └── marts/               ← Gold layer: business dimensions + fact table
│       ├── dim_date.sql
│       ├── dim_product.sql
│       ├── dim_customer.sql
│       └── fact_order_items.sql
│
├── seeds/                   ← Static CSV data loaded directly to Snowflake
│   └── fact_order_items_seed.csv
│
├── snapshots/               ← SCD2 snapshots — capture history when data changes
│   ├── products_snapshot.sql
│   └── customers_snapshot.sql
│
├── macros/                  ← Custom dbt macros (placeholder)
├── dbt_packages/            ← Installed packages (dbt_utils)
└── logs/                    ← dbt execution logs (git-ignored)
```

---

## Data flow
```
Snowflake RAW (loaded by ingestion pipeline)
    │
    ├── 1. Staging (Silver) — dbt run --select staging.*
    │   ├── stg_products   → deduplicate + flatten rating VARIANT
    │   ├── stg_users      → deduplicate + flatten name/address VARIANT
    │   └── stg_carts      → deduplicate + LATERAL FLATTEN products array
    │
    ├── 2. Snapshots (SCD2) — dbt snapshot
    │   ├── products_snapshot  → new row written when price/category/rating changes
    │   └── customers_snapshot → new row written when email/name/address/phone changes
    │
    └── 3. Marts (Gold) — dbt run --select marts.*
        ├── dim_date           → generated date spine (2024-01-01, 730 days)
        ├── dim_product        → full SCD2 history from products_snapshot (all versions)
        ├── dim_customer       → full SCD2 history from customers_snapshot (all versions)
        └── fact_order_items   → pipeline rows (stg_carts + dims)
                                 UNION ALL seed rows (fact_order_items_seed + dims)
```

---

## Models explained

### staging/sources.yml
Declares the three RAW tables as dbt sources. This is what allows
staging models to use `{{ source('raw', 'products') }}` instead of
hardcoding `ECOMMERCE_DB.RAW.PRODUCTS`.

Also defines data quality tests that run with `dbt test`:
- `products`: not_null on id, title, price, category, _loaded_at, _run_id
- `users`: not_null on id, email, _loaded_at
- `carts`: not_null on id, userid, _loaded_at

---

### staging/stg_products.sql
**Source:** `RAW.PRODUCTS`
**Output:** `STAGING.STG_PRODUCTS` (table)

What it does:
1. Deduplicates using `ROW_NUMBER() OVER (PARTITION BY id, _run_id ORDER BY _loaded_at DESC)`
   — keeps the most recently loaded record per product per pipeline run
2. Renames columns to standard names (`id → product_id`, `title → product_name`)
3. Flattens the `rating` VARIANT column into two scalar columns:
   - `rating:rate::float  → rating_score`
   - `rating:count::integer → rating_count`

---

### staging/stg_users.sql
**Source:** `RAW.USERS`
**Output:** `STAGING.STG_USERS` (table)

What it does:
1. Deduplicates using the same `ROW_NUMBER()` pattern as stg_products
2. Flattens the `name` VARIANT: `name:firstname → first_name`, `name:lastname → last_name`
3. Flattens the `address` VARIANT into scalar columns:
   - `address:city`, `address:street`, `address:zipcode`
   - `address:geolocation:lat::float → latitude`
   - `address:geolocation:long::float → longitude`

---

### staging/stg_carts.sql
**Source:** `RAW.CARTS`
**Output:** `STAGING.STG_CARTS` (table)

What it does:
1. Deduplicates at the cart level using `ROW_NUMBER()`
2. Uses `LATERAL FLATTEN(input => c.products)` to explode the `products` VARIANT array
   — each item in a cart becomes its own row
3. Extracts `productId` and `quantity` from each array element

This is the most important staging transformation — a single cart with
3 products becomes 3 rows, one per product, ready to join against dim_product.

---

### marts/dim_date.sql
**Source:** no upstream dbt models — self-contained
**Output:** `MARTS.DIM_DATE` (view)

Generates a date spine of 730 days starting from 2024-01-01 using
Snowflake's `TABLE(GENERATOR(ROWCOUNT => 730))`.

Columns: `date_key` (YYYYMMDD integer for fast joins), `full_date`,
`day_of_week`, `day_name`, `month`, `month_name`, `quarter`, `year`, `is_weekend`

The `date_key` format (e.g. `20260328`) is used as the join key in `fact_order_items`.

---

### marts/dim_product.sql
**Source:** `{{ ref('products_snapshot') }}`
**Output:** `MARTS.DIM_PRODUCT` (view)

Reads all rows from `products_snapshot` — no `WHERE dbt_valid_to IS NULL` filter,
so every historical version of a product is included (full SCD2 history).

Surrogate key is generated from `(product_id, dbt_valid_from)` — not just
`product_id` alone — because the same product now has multiple rows (one per
version), and the key must be unique across all of them.

Exposes `effective_from` and `effective_to` so downstream consumers can filter
to whichever version was current at a given point in time.

---

### marts/dim_customer.sql
**Source:** `{{ ref('customers_snapshot') }}`
**Output:** `MARTS.DIM_CUSTOMER` (view)

Same pattern as dim_product — keeps all historical versions, no current-row filter.

Surrogate key generated from `(user_id, dbt_valid_from)`.
Concatenates `first_name || ' ' || last_name → full_name`.
Exposes `effective_from` and `effective_to` for point-in-time joins.

---

### marts/fact_order_items.sql
**Sources:** `stg_carts`, `fact_order_items_seed`, `dim_product`, `dim_customer`, `dim_date`
**Output:** `MARTS.FACT_ORDER_ITEMS` (view)

The central fact table of the star schema. Combines two data sources via `UNION ALL`:

**pipeline_orders CTE** — live data from the ingestion pipeline:
- `stg_carts` provides the grain: one row per cart-product combination
- `dim_product` provides `product_key` and `price` (for `unit_price`)
- `dim_customer` provides `customer_key`
- `dim_date` provides `date_key` (joined via `TO_NUMBER(TO_CHAR(cart_date, 'YYYYMMDD'))`)
- Calculates `total_price = quantity * unit_price`
- Generates a surrogate key from `(cart_id, product_id)`

**seed_orders CTE** — static data from `fact_order_items_seed`:
- Same dimension joins (dim_product, dim_customer, dim_date) to resolve surrogate keys
- Uses pre-computed `unit_price` and `total_price` directly from the seed
- Generates a surrogate key from `order_item_id`
- `loaded_at` and `run_id` are `null` (no pipeline metadata for seed rows)

Both CTEs produce identical columns and are combined with `UNION ALL` in `final`.

---

## Seeds

### seeds/fact_order_items_seed.csv
A CSV file with pre-built order items data (columns: `order_item_id`,
`order_id`, `user_id`, `product_id`, `quantity`, `unit_price`, `total_price`,
`order_date`).

Running `dbt seed` creates a table `FACT_ORDER_ITEMS_SEED` in the `MARTS` schema
(configured via `seeds: +schema: MARTS` in `dbt_project.yml`).

`fact_order_items.sql` references this seed via `{{ ref('fact_order_items_seed') }}`
and unions it with live pipeline data. This means `FACT_ORDER_ITEMS` always
contains both sources — you must run `dbt seed` before `dbt run` for the
fact table to include the seed rows.

```bash
dbt seed                                        # load all seeds
dbt seed --select fact_order_items_seed         # load this seed only
dbt seed --full-refresh                         # drop and recreate from scratch
```

---

## Snapshots

Snapshots implement SCD Type 2 — they detect when a row changes and write
the old version with a closing timestamp (`dbt_valid_to`) before inserting
the new version. This preserves full history rather than overwriting.

dbt adds four columns automatically to every snapshot table:
- `dbt_scd_id` — unique row identifier
- `dbt_updated_at` — when this snapshot row was last updated
- `dbt_valid_from` — when this version became active
- `dbt_valid_to` — when this version was superseded (`null` = currently active)

Both snapshots use `strategy='check'` — dbt compares the listed columns on
every run and creates a new row only when at least one of them has changed.

---

### snapshots/products_snapshot.sql
**Source:** `{{ ref('stg_products') }}`
**Output:** `MARTS.PRODUCTS_SNAPSHOT` (snapshot table)

Tracked columns: `price`, `category`, `rating_score`, `rating_count`

If a product's price changes between pipeline runs, the snapshot will:
1. Close the old row — set `dbt_valid_to` to the current timestamp
2. Insert a new row — `dbt_valid_from` = now, `dbt_valid_to` = null

`invalidate_hard_deletes=True` — if a product disappears from staging
(i.e. was deleted from the source), its snapshot row is closed automatically.

---

### snapshots/customers_snapshot.sql
**Source:** `{{ ref('stg_users') }}`
**Output:** `MARTS.CUSTOMERS_SNAPSHOT` (snapshot table)

Tracked columns: `email`, `first_name`, `last_name`, `city`, `street`, `zipcode`, `phone`

Same behaviour as products_snapshot. If a customer updates their address
or email, a new version row is written and the old one is closed.

`invalidate_hard_deletes=True` — deleted customers are automatically closed.

---

## Packages

### dbt_utils (v1.1.1)
Installed from `dbt-labs/dbt_utils`. Used in this project for:

- `dbt_utils.generate_surrogate_key([...])` — generates an MD5 hash from a list
  of columns to create a stable surrogate key. Used in `dim_product`,
  `dim_customer`, and `fact_order_items`.

Install packages after cloning:
```bash
dbt deps
```

---

## How to run

Make sure your virtual environment is active and `.env` is filled in.

```bash
# navigate to the dbt folder
cd dbt

# install packages (first time only)
dbt deps

# test Snowflake connection
dbt debug

# load seed data — must run BEFORE dbt run so fact_order_items can union it
dbt seed

# run staging models only
dbt run --select staging.*

# run snapshots — must run AFTER staging, BEFORE marts
dbt snapshot

# run mart models only
dbt run --select marts.*

# run everything in correct order (seed must already be loaded)
dbt run && dbt snapshot && dbt run --select marts.*

# run data quality tests
dbt test

# run seed + models + snapshots + tests in one command (recommended)
dbt build
```

Expected output for `dbt snapshot`:
```
12:00:01  Running with dbt=1.x.x
12:00:02  Found 7 models, 9 tests, 1 seed, 2 snapshots
12:00:03  Concurrency: 4 threads (target='dev')
12:00:04  1 of 2 START snapshot MARTS.products_snapshot .................. [RUN]
12:00:06  1 of 2 OK snapshotted MARTS.products_snapshot .................. [SUCCESS]
12:00:06  2 of 2 START snapshot MARTS.customers_snapshot ................. [RUN]
12:00:07  2 of 2 OK snapshotted MARTS.customers_snapshot ................. [SUCCESS]
12:00:07  Completed successfully
```

Expected output for `dbt run`:
```
12:00:01  Running with dbt=1.x.x
12:00:02  Found 7 models, 9 tests, 1 seed, 2 snapshots
12:00:03  Concurrency: 4 threads (target='dev')
12:00:04  1 of 7 START sql table model STAGING.stg_products .............. [RUN]
12:00:06  1 of 7 OK created sql table model STAGING.stg_products ......... [SUCCESS]
12:00:06  2 of 7 START sql table model STAGING.stg_users ................. [RUN]
12:00:07  2 of 7 OK created sql table model STAGING.stg_users ............ [SUCCESS]
12:00:07  3 of 7 START sql table model STAGING.stg_carts ................. [RUN]
12:00:08  3 of 7 OK created sql table model STAGING.stg_carts ............ [SUCCESS]
12:00:08  4 of 7 START sql view model MARTS.dim_date ..................... [RUN]
12:00:09  4 of 7 OK created sql view model MARTS.dim_date ................ [SUCCESS]
12:00:09  5 of 7 START sql view model MARTS.dim_product .................. [RUN]
12:00:10  5 of 7 OK created sql view model MARTS.dim_product ............. [SUCCESS]
12:00:10  6 of 7 START sql view model MARTS.dim_customer ................. [RUN]
12:00:11  6 of 7 OK created sql view model MARTS.dim_customer ............ [SUCCESS]
12:00:11  7 of 7 START sql view model MARTS.fact_order_items ............. [RUN]
12:00:12  7 of 7 OK created sql view model MARTS.fact_order_items ........ [SUCCESS]
12:00:12  Completed successfully
```

---

## Snowflake output structure

```
ECOMMERCE_DB
├── RAW                        ← written by ingestion pipeline (input to dbt)
│   ├── PRODUCTS
│   ├── USERS
│   └── CARTS
│
├── STAGING                    ← written by dbt staging models (tables)
│   ├── STG_PRODUCTS
│   ├── STG_USERS
│   └── STG_CARTS
│
└── MARTS                      ← written by dbt snapshots + mart models
    ├── PRODUCTS_SNAPSHOT      ← written by dbt snapshot (SCD2 history table)
    ├── CUSTOMERS_SNAPSHOT     ← written by dbt snapshot (SCD2 history table)
    ├── FACT_ORDER_ITEMS_SEED  ← written by dbt seed
    ├── DIM_DATE               ← written by dbt run (view)
    ├── DIM_PRODUCT            ← written by dbt run (view)
    ├── DIM_CUSTOMER           ← written by dbt run (view)
    └── FACT_ORDER_ITEMS       ← written by dbt run (view)
```

---

## Design decisions

**Why is staging materialised as TABLE and marts as VIEW?**
Staging models do heavy work — deduplication and VARIANT flattening on the
full RAW table. Materialising as a table means that work runs once at
`dbt run` time. Mart models are simple joins on already-clean data,
so views are fine — they stay lightweight and always reflect the latest
staging state without needing to be re-run separately.

**Why deduplicate in staging instead of RAW?**
The ingestion pipeline uses `ON_ERROR = 'CONTINUE'`, which means if the
pipeline runs twice on the same day, duplicate records can exist in RAW.
Deduplication in staging on `(id, _run_id)` ensures each record appears
exactly once in the Silver layer without touching the immutable RAW tables.

**Why LATERAL FLATTEN in stg_carts?**
The FakeStoreAPI returns each cart as one row with a `products` JSON array.
A fact table needs one row per product per cart. LATERAL FLATTEN explodes
the array in SQL, giving each item its own row — this is the right place
to do it because all downstream models expect the exploded grain.

**Why use surrogate keys in the mart layer?**
Natural keys (like `product_id` from the API) are not unique across SCD2 history —
the same `product_id` appears multiple times, once per version. A surrogate key
built from `(product_id, dbt_valid_from)` or `(user_id, dbt_valid_from)` is
unique per version row, making it safe to use as a primary key in the dimension
and as a foreign key in the fact table.

**Why do dim_product and dim_customer keep ALL versions instead of current only?**
Keeping all versions (`dbt_valid_to IS NULL` removed) allows `fact_order_items`
to join against the exact version of a product or customer that was active at
the time of the order. For example, if a product's price was $50 when an order
was placed but is now $75, the fact table correctly records $50 — not the
current price. This is the core value of SCD Type 2.

**Why use `strategy='check'` instead of `strategy='timestamp'`?**
The FakeStoreAPI does not return an `updated_at` timestamp on records.
The `check` strategy compares specific column values on every run and creates
a new snapshot row when any tracked column changes — no timestamp needed.
The trade-off is a full column comparison on every `dbt snapshot` run.

**Why does fact_order_items UNION ALL the seed instead of joining it?**
The seed and the pipeline represent two independent sources of order data —
they share the same grain (one row per order item) but come from different
origins. A UNION ALL is the correct pattern to combine two datasets of the
same shape. A join would be wrong here because there is no shared key between
a seed row and a pipeline row to join on.

**Why does seed_orders null out loaded_at and run_id?**
Those columns are pipeline metadata — they track when the ingestion job ran
and which run produced the record. The seed has no pipeline run behind it,
so these are set to null rather than inventing fake values. Downstream
queries can use `WHERE run_id IS NOT NULL` to isolate pipeline rows if needed.

**Why does fact_order_items_seed land in MARTS schema?**
Configured via `seeds: +schema: MARTS` in `dbt_project.yml`. This keeps
the seed table co-located with the models that reference it and avoids it
appearing in STAGING alongside cleaned source data.

**Why is dim_date a generated spine instead of a seed?**
A date spine generated in SQL requires zero maintenance — it never needs
to be updated and has no file to manage. A seed CSV would need to be
regenerated every year. The Snowflake `GENERATOR` function makes this trivial.

---

## Environment variables required

Loaded from `.env` via `profiles.yml`:

| Variable | Purpose |
|---|---|
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier |
| `SNOWFLAKE_USER` | Snowflake username |
| `SNOWFLAKE_PASSWORD` | Snowflake password |
| `SNOWFLAKE_ROLE` | Role used for transformations (TRANSFORMER or SYSADMIN) |
| `SNOWFLAKE_DATABASE` | Target database (ECOMMERCE_DB) |
| `SNOWFLAKE_WAREHOUSE` | Compute warehouse (COMPUTE_WH) |
