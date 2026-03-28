-- ── switch to loader role and raw schema ─────────────────────
USE ROLE SYSADMIN;
USE DATABASE ECOMMERCE_DB;
USE SCHEMA RAW;
USE WAREHOUSE ECOMMERCE_WH;

-- ── products ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS RAW.PRODUCTS (
    id              NUMBER,
    title           VARCHAR,
    price           FLOAT,
    description     VARCHAR,
    category        VARCHAR,
    image           VARCHAR,
    rating          VARIANT,
    _loaded_at      TIMESTAMP_TZ,
    _source         VARCHAR,
    _entity         VARCHAR,
    _load_date      DATE,
    _run_id         VARCHAR
);

-- ── users ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS RAW.USERS (
    id              NUMBER,
    email           VARCHAR,
    username        VARCHAR,
    password        VARCHAR,
    name            VARIANT,
    address         VARIANT,
    phone           VARCHAR,
    _loaded_at      TIMESTAMP_TZ,
    _source         VARCHAR,
    _entity         VARCHAR,
    _load_date      DATE,
    _run_id         VARCHAR
);

-- ── carts ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS RAW.CARTS (
    id              NUMBER,
    userid          NUMBER,
    date            TIMESTAMP_TZ,
    products        VARIANT,
    _loaded_at      TIMESTAMP_TZ,
    _source         VARCHAR,
    _entity         VARCHAR,
    _load_date      DATE,
    _run_id         VARCHAR
);

-- ── json file format ──────────────────────────────────────────
CREATE FILE FORMAT IF NOT EXISTS raw_json_format
    TYPE = 'JSON'
    STRIP_OUTER_ARRAY = TRUE
    COMPRESSION = 'AUTO';

-- ── s3 stage (credentials from .env) ─────────────────────────
-- NOTE: replace placeholders with your actual AWS credentials
-- This is run once manually during setup only
CREATE STAGE IF NOT EXISTS raw_s3_stage
    URL = 's3://retail-fcmg-api-aws-snowflake-dbt/raw/'
    CREDENTIALS = (
        aws_key_id = 'YOUR_AWS_ACCESS_KEY_ID'
        aws_secret_key = 'YOUR_AWS_SECRET_ACCESS_KEY'
    )
    FILE_FORMAT = raw_json_format;