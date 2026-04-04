import requests
from typing import List, Dict, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging
from ingestion.core.config import get_settings
from ingestion.core.logger import get_logger

logger = get_logger(__name__)

class APIClient:

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.fakestore_base_url
        self.session =  requests.Session()      

    @retry(
        stop =          stop_after_attempt(3),
        wait =          wait_exponential(multiplier=1, min=2, max=10),
        retry =         retry_if_exception_type(requests.exceptions.ConnectionError),
        before_sleep =  before_sleep_log(logger, logging.WARNING),   
    )
    def get(self, endpoint: str) -> List[Dict]:
        url = f"{self.base_url}/{endpoint}"
        logger.info(f"Fetching {url}")

        response = self.session.get(url, timeout = 10)
        response.raise_for_status()

        data = response.json()
        logger.info(f"Received {len(data)} records from {endpoint}")

        return data