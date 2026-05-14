import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ChillerParser:
    @staticmethod
    def parse_schedule(response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse The Chiller's JSON response for rink schedule.
        The endpoint returns JSON directly.
        """
        try:
            data = json.loads(response_text)
            logger.info("Successfully parsed Chiller schedule JSON")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Chiller response as JSON: {e}")
            # Try to extract JSON from HTML if response is HTML
            if '<' in response_text:
                logger.warning("Response appears to be HTML, attempting to extract JSON...")
                return ChillerParser._extract_json_from_html(response_text)
            return None

    @staticmethod
    def _extract_json_from_html(html: str) -> Optional[Dict]:
        """Attempt to extract JSON from HTML response."""
        import re
        # Look for JSON-like patterns in the HTML
        json_match = re.search(r'\{[\s\S]*\}', html)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def normalize_schedule(data: Dict) -> Dict:
        """
        Normalize Chiller schedule data to standard format.
        Handles various possible response structures.
        """
        normalized = {
            "rink_name": "The Chiller",
            "location_id": 0,
            "schedule": []
        }

        # Handle various possible data structures
        if isinstance(data, dict):
            # If data has a schedule key
            if 'schedule' in data:
                normalized["schedule"] = data['schedule']
            # If data has events key
            elif 'events' in data:
                normalized["schedule"] = data['events']
            # If data has games key
            elif 'games' in data:
                normalized["schedule"] = data['games']
            # If the entire response is the schedule array
            elif isinstance(data, list):
                normalized["schedule"] = data
            else:
                # Just include the whole response
                normalized["data"] = data

        logger.info(f"Normalized Chiller schedule with {len(normalized['schedule'])} events")
        return normalized
