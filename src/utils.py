import json
import logging
import os
import time
import requests
from typing import Any, Dict, List, Optional
from config import DATA_DIR, TEAMS_DIR, LOG_LEVEL, MAX_RETRIES, RETRY_BACKOFF

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_data_directories() -> None:
    """Ensure data directories exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(TEAMS_DIR, exist_ok=True)
    logger.info(f"Data directories ready: {DATA_DIR}")


def save_json(filename: str, data: Any, directory: str = DATA_DIR) -> None:
    """Save data to a JSON file with pretty formatting."""
    filepath = os.path.join(directory, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved JSON to {filepath}")


def load_json(filename: str, directory: str = DATA_DIR) -> Dict:
    """Load data from a JSON file."""
    filepath = os.path.join(directory, filename)

    if not os.path.exists(filepath):
        logger.warning(f"File not found: {filepath}")
        return {}

    with open(filepath, 'r') as f:
        return json.load(f)


def http_get(url: str, timeout: int = 10, headers: Optional[Dict] = None) -> Optional[str]:
    """Make a GET request with retry logic."""
    headers = headers or {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for {url}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF ** attempt)
            else:
                logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts")
                return None


def http_post(url: str, data: Dict = None, timeout: int = 10, headers: Optional[Dict] = None) -> Optional[str]:
    """Make a POST request with retry logic."""
    request_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    if headers:
        request_headers.update(headers)

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, data=data, timeout=timeout, headers=request_headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for POST {url}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF ** attempt)
            else:
                logger.error(f"Failed to POST {url} after {MAX_RETRIES} attempts")
                return None
