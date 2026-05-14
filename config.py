import os

SISU_URL = "https://www.sisuthunderbirds.com"
CHILLER_URL = "https://www.thechiller.com/schedule_json.cfm?LocationID=0"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TEAMS_DIR = os.path.join(DATA_DIR, "teams")

REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_BACKOFF = 0.5

LOG_LEVEL = "INFO"
