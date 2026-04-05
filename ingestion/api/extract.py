from ingestion.mock_data import PRODUCTS, USERS, CARTS
from ingestion.core.logger import get_logger
from typing import List, Dict, Any

logger = get_logger(__name__)

class FakeStoreExtractor:

    def __init__(self):
        pass  # No API client needed anymore

    def extract_products(self) -> List[Dict]:
        logger.info(f"Extracting products from mock data")
        logger.info(f"Extracted {len(PRODUCTS)} products")
        return PRODUCTS

    def extract_users(self) -> List[Dict]:
        logger.info(f"Extracting users from mock data")
        logger.info(f"Extracted {len(USERS)} users")
        return USERS

    def extract_carts(self) -> List[Dict]:
        logger.info(f"Extracting carts from mock data")
        logger.info(f"Extracted {len(CARTS)} carts")
        return CARTS

    def extract_all(self) -> Dict[str, List[Dict]]:
        logger.info("Starting full extraction from mock data")

        results = {
            "products": self.extract_products(),
            "users":    self.extract_users(),
            "carts":    self.extract_carts(),
        }

        total = sum(len(v) for v in results.values())
        logger.info(f"Full extraction complete - {total} total records")

        return results