from ingestion.api.api_client import APIClient
from ingestion.core.logger import get_logger
from typing import List, Dict, Any

logger = get_logger(__name__)

class FakeStoreExtractor:

    def __init__(self):
        self.client = APIClient()

    def extract_products(self) -> List[Dict]:
        logger.info("Extracting products")
        data = self.client.get("products")
        logger.info(f"Extracted {len(data)} products")
        return data
    
    def extract_users(self) -> List[Dict]:
        logger.info("Extracting users")
        data = self.client.get("users")
        logger.info(f"Extracted {len(data)} users")
        return data
    
    def extract_carts(self) -> List[Dict]:
        logger.info("Extracting carts")
        data = self.client.get("carts")
        logger.info(f"Extracted {len(data)} carts")
        return data
    
    def extract_all(self) -> Dict[str, List[Dict]]:
        logger.info("Starting full extracting from FakeStoreAPI")

        results = {
            "products":     self.extract_products(),
            "users":        self.extract_users(),
            "carts":        self.extract_carts(),
        }

        total = sum(len(v) for v in results.values())
        logger.info(f"Full extraction complete - {total} total records")

        return results