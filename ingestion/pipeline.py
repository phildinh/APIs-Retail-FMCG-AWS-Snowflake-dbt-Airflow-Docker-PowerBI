import uuid
from ingestion.api.extract import FakeStoreExtractor
from ingestion.storage.load import load_to_s3
from ingestion.storage.copy_into_snowflake import copy_raw_to_snowflake
from ingestion.core.logger import get_logger
from ingestion.core.utils import get_run_date, enrich_records
from ingestion.core.config import get_settings


logger = get_logger(__name__)


def run_pipeline() -> None:
    run_id = str(uuid.uuid4())
    run_date = get_run_date()
    settings = get_settings()

    logger.info(f"Pipeline started — run_id: {run_id} run_date: {run_date}")

    # task 1 — extract from API and load to S3
    extractor = FakeStoreExtractor()
    results = extractor.extract_all()

    s3_keys = {}
    for entity, data in results.items():
        enriched = enrich_records(
            entity=entity,
            data=data,
            run_id=run_id
        )
        logger.info(f"Loading {entity} to S3")
        s3_key = load_to_s3(entity=entity, data=enriched)
        s3_keys[entity] = s3_key
        logger.info(f"{entity} landed at {s3_key}")

    logger.info("S3 loading complete — summary:")
    for entity, key in s3_keys.items():
        logger.info(f"  {entity}: s3://{settings.aws_bucket_name}/{key}")

    # task 2 — copy from S3 to Snowflake RAW
    logger.info("Starting Snowflake ingestion")
    copy_results = copy_raw_to_snowflake(
        s3_keys=s3_keys,
        run_id=run_id
    )

    logger.info("Pipeline complete — rows loaded to Snowflake:")
    for entity, count in copy_results.items():
        logger.info(f"  {entity}: {count} rows")


if __name__ == "__main__":
    run_pipeline()