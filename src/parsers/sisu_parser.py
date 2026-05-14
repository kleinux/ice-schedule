import logging
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class SisuParser:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None

    def fetch_teams(self, html: str) -> List[Tuple[str, str]]:
        """
        Parse homepage to find all team links.
        Returns list of (team_name, team_url) tuples.
        """
        soup = BeautifulSoup(html, 'html.parser')
        teams = []

        # Strategy: Look for common patterns in sports websites
        # Try to find links containing "schedule" or team names
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)

            # Look for schedule links
            if 'schedule' in href.lower() and text and len(text) > 0:
                full_url = urljoin(self.base_url, href)
                # Avoid duplicates
                if not any(url == full_url for _, url in teams):
                    teams.append((text, full_url))
                    logger.debug(f"Found team: {text} -> {full_url}")

        if not teams:
            logger.warning("No team links found with standard patterns")
            # Try alternative: look for any links that might be teams
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if href and text and len(text) > 2 and len(text) < 50:
                    full_url = urljoin(self.base_url, href)
                    if 'team' in full_url.lower() or any(c.isupper() for c in text):
                        if not any(url == full_url for _, url in teams):
                            teams.append((text, full_url))

        logger.info(f"Found {len(teams)} potential teams")
        return teams

    def parse_schedule(self, html: str, team_name: str) -> List[Dict]:
        """
        Parse a team schedule page and extract games.
        Returns list of game dictionaries.
        """
        soup = BeautifulSoup(html, 'html.parser')
        schedule = []

        # Look for table rows or game containers
        rows = soup.find_all('tr')
        if not rows:
            rows = soup.find_all('div', class_=re.compile(r'game|match|event', re.I))

        for row in rows:
            game = self._parse_game_row(row, team_name)
            if game:
                schedule.append(game)
                logger.debug(f"Parsed game: {game}")

        logger.info(f"Found {len(schedule)} games for {team_name}")
        return schedule

    def _parse_game_row(self, row, team_name: str) -> Optional[Dict]:
        """Extract game details from a row or element."""
        cells = row.find_all(['td', 'div'])
        if len(cells) < 3:
            return None

        text_content = ' '.join([cell.get_text(strip=True) for cell in cells])

        # Check if this looks like a game row (contains date/time indicators)
        if not any(indicator in text_content for indicator in
                   ['AM', 'PM', 'am', 'pm', ':', 'vs', 'vs.', '@', 'game', 'match']):
            return None

        game = {
            "date": None,
            "time": None,
            "opponent": None,
            "location": None,
            "game_type": None,
            "status": None
        }

        # Try to extract date
        date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text_content)
        if date_match:
            try:
                date_str = date_match.group(1)
                game["date"] = self._normalize_date(date_str)
            except:
                pass

        # Try to extract time
        time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?', text_content)
        if time_match:
            hour = time_match.group(1)
            minute = time_match.group(2)
            ampm = time_match.group(3)
            if ampm and ampm.upper() == 'PM' and int(hour) != 12:
                hour = str(int(hour) + 12)
            elif ampm and ampm.upper() == 'AM' and int(hour) == 12:
                hour = '00'
            game["time"] = f"{hour.zfill(2)}:{minute}"

        # Determine game type (Home/Away)
        if '@' in text_content or 'at ' in text_content.lower():
            game["game_type"] = "Away"
        else:
            game["game_type"] = "Home"

        # Extract opponent and location
        opponent_match = re.search(r'(?:vs\.?|@)\s*(.+?)(?:\s+at\s+|\s+$|$)', text_content, re.I)
        if opponent_match:
            game["opponent"] = opponent_match.group(1).strip()

        location_match = re.search(r'at\s+(.+?)(?:\s+$|$)', text_content, re.I)
        if location_match:
            game["location"] = location_match.group(1).strip()

        # Check for result status
        if 'final' in text_content.lower() or 'completed' in text_content.lower():
            game["status"] = "Final"
        elif 'scheduled' in text_content.lower() or 'upcoming' in text_content.lower():
            game["status"] = "Scheduled"

        # Only return if we have at least a date
        if game["date"]:
            return game

        return None

    def _normalize_date(self, date_str: str) -> str:
        """Convert various date formats to ISO 8601 (YYYY-MM-DD)."""
        formats = ['%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%m-%d-%y', '%d/%m/%Y', '%d-%m-%Y']
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                continue
        logger.warning(f"Could not parse date: {date_str}")
        return date_str
