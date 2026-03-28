import boto3
import snowflake.connector
from snowflake.connector import SnowflakeConnection
from functools import lru_cache
from ingestion.core.config import get_settings
from ingestion.core.logger import get_logger

logger = get_logger(__name__)

def get_snowflake_connection() -> SnowflakeConnection:
    settings = get_settings()
    logger.info("Opening Snowflake connection")

    connection =    snowflake.connector.connect(
        account =   settings.snowflake_account,
        user =      settings.snowflake_user,
        password =  settings.snowflake_password,
        warehouse = settings.snowflake_warehouse,
        database =  settings.snowflake_database,
        schema =    settings.snowflake_schema,
        role =      "LOADER",
    )

    logger.info("Snowflake connection established")
    return connection

@lru_cache
def get_s3_client():
    settings = get_settings()
    logger.info("Creating S3 client")

    client = boto3.client(
        "s3",
        aws_access_key_id =     settings.aws_access_key_id,
        aws_secret_access_key = settings.aws_secret_access_key,
        region_name =           settings.aws_region
    )

    logger.info("S3 client created")
    return client