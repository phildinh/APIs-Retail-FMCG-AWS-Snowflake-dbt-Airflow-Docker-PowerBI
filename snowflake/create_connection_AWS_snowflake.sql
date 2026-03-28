USE ROLE SYSADMIN;
USE DATABASE ECOMMERCE_DB;
USE SCHEMA RAW;
USE WAREHOUSE ECOMMERCE_WH;

-- file format for JSON
CREATE FILE FORMAT IF NOT EXISTS raw_json_format
    TYPE = 'JSON'
    STRIP_OUTER_ARRAY = TRUE
    COMPRESSION = 'AUTO';

-- stage with credentials stored securely here once
CREATE STAGE IF NOT EXISTS raw_s3_stage
    URL = 's3://retail-fcmg-api-aws-snowflake-dbt/raw/'
    CREDENTIALS = (
        aws_key_id = 'Your_key'
        aws_secret_key = 'Your_sceret_key'
    )
    FILE_FORMAT = raw_json_format;

LIST @raw_s3_stage;