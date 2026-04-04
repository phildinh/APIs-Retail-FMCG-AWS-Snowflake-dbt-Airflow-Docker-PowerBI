import json
from typing import List, Dict, Any
from ingestion.storage.db import get_s3_client
from ingestion.core.config import get_settings
from ingestion.core.logger import get_logger
from ingestion.core.utils import format_s3_key

logger = get_logger(__name__)

def load_to_s3(entity: str, data: List[Dict]) -> str:
    settings = get_settings()
    client = get_s3_client()

    s3_key = format_s3_key(entity)
    payload = json.dumps(data, indent = 2, default = str)

    logger.info(f"Loading {len(data)} {entity} records to S3")

    client.put_object(
        Bucket =        settings.aws_bucket_name,
        Key =           s3_key,
        Body =          payload,
        ContentType =   "application/json",
    )

    logger.info(f"Successfully loaded to s3://{settings.aws_bucket_name}/{s3_key}")

    return s3_key