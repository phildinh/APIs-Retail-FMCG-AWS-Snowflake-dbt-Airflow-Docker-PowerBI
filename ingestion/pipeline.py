from ingestion.api.extract import FakeStoreExtractor
from ingestion.storage.load import load_to_s3
from ingestion.core.logger import get_logger
from ingestion.core.utils import get_run_date
from ingestion.core.config import get_settings

logger = get_logger(__name__)

def run_pipeline() -> None:
    run_date = get_run_date()
    settings = get_settings()
    logger.info(f"Pipeline started - run date: {run_date}")

    extractor = FakeStoreExtractor()
    results = extractor.extract_all()

    s3_keys = {}
    for entity, data in results.items():
        logger.info(f"Loading {entity} to S3")
        s3_key = load_to_s3(entity=entity, data=data)
        s3_keys[entity] = s3_key
        logger.info(f"{entity} loaded to {s3_key}")

    logger.info("Pipeline complete - summary: ")
    for entity, key in s3_keys.items():
        logger.info(f" {entity}: s3://{settings.aws_bucket_name}/{key}")

if __name__ == "__main__":
    run_pipeline()