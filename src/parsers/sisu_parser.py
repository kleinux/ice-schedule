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
        self.current_year = datetime.now().year

    def fetch_teams(self, html: str) -> List[Tuple[str, str]]:
        """
        Parse homepage to find team links from the Teams dropdown menu.
        Returns list of (team_name, team_calendar_url) tuples.
        """
        soup = BeautifulSoup(html, 'html.parser')
        teams = []

        # Look for "Teams" link and its dropdown menu
        for link in soup.find_all('a', string=lambda x: x and 'Teams' in x):
            # Find the parent element that contains the dropdown
            parent = link.find_parent(['li', 'div'])
            if parent:
                # Look for dropdown menu
                dropdown = parent.find('ul', class_='dropdown-menu')
                if dropdown:
                    # Find all team links in the dropdown
                    for team_link in dropdown.find_all('a', href=True):
                        team_url = team_link.get('href', '')
                        team_name = team_link.get_text(strip=True)

                        # Team links should be in format /team/{id}
                        if '/team/' in team_url:
                            # Convert to calendar URL
                            calendar_url = urljoin(self.base_url, f"{team_url}/calendar")
                            teams.append((team_name, calendar_url))
                            logger.debug(f"Found team: {team_name} -> {calendar_url}")

        if teams:
            logger.info(f"Found {len(teams)} teams from Teams menu")
        else:
            logger.warning("No teams found in Teams dropdown menu")

        return teams

    def parse_calendar(self, html: str, team_name: str) -> List[Dict]:
        """
        Parse a team's calendar page and extract all events.
        Returns list of event dictionaries.
        """
        soup = BeautifulSoup(html, 'html.parser')
        events = []

        # Find all calendar events
        for event_div in soup.find_all('div', class_='calendar_event'):
            event = self._parse_event(event_div)
            if event:
                events.append(event)
                logger.debug(f"Parsed event: {event}")

        logger.info(f"Found {len(events)} events for {team_name}")
        return events

    def _parse_event(self, event_div) -> Optional[Dict]:
        """Extract event details from a calendar_event div."""
        # Get event type (game, practice, meeting, etc.)
        event_type_span = event_div.find('span', class_='calendar_event_type')
        event_type = event_type_span.get_text(strip=True).split()[0] if event_type_span else None

        # Get time
        time_span = event_div.find('span', class_='calendar_event_time')
        time = time_span.get_text(strip=True) if time_span else None

        # Get opponent/activity
        opponent_span = event_div.find('span', class_='calendar_event_opponent')
        opponent = opponent_span.get_text(strip=True) if opponent_span else None

        # Get location
        location_span = event_div.find('span', class_='calendar_event_location')
        location = location_span.get_text(strip=True) if location_span else None

        # Get duration
        duration_span = event_div.find('span', class_='calendar_event_duration')
        duration = duration_span.get_text(strip=True) if duration_span else None

        # Find the date from the mobile_event div (contains full date like "MAY14")
        date_str = None
        mobile_event = event_div.find_parent('div', class_='mobile_event')
        if mobile_event:
            text = mobile_event.get_text(strip=True)
            # Extract date from format like "MAY14" or "JUN1" at the beginning
            month_match = re.match(r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d{1,2})', text)
            if month_match:
                month_str = month_match.group(1)
                day_str = month_match.group(2)
                date_str = f"{month_str}{day_str}"

        event = {
            "date": self._parse_calendar_date(date_str) if date_str else None,
            "time": time,
            "event_type": event_type,
            "opponent": opponent,
            "location": location,
            "duration": duration
        }

        # Only include if we have at least a type and date
        if event["event_type"] and event["date"]:
            return event

        return None

    def _parse_calendar_date(self, date_str: str) -> Optional[str]:
        """Convert calendar date to ISO 8601 format."""
        if not date_str:
            return None

        # Handle month abbreviation + day (e.g., "MAY14", "JUN1")
        date_str = date_str.strip()

        # Try month name + day pattern
        month_map = {
            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
        }

        # Extract month and day
        match = re.match(r'([A-Z]{3})(\d{1,2})', date_str, re.IGNORECASE)
        if match:
            month_str = match.group(1).upper()
            day = int(match.group(2))

            if month_str in month_map:
                month = month_map[month_str]
                # Determine year - assume current year or next year if month is earlier
                month_num = month
                current_month = datetime.now().month
                year = self.current_year

                # If the month is earlier than current month, it might be next year
                if month_num < current_month:
                    year += 1

                try:
                    date_obj = datetime(year, month, day)
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    logger.warning(f"Invalid date: {month_str} {day}")
                    return None

        # Try numeric formats
        for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%m-%d-%y']:
            try:
                parsed = datetime.strptime(date_str, fmt)
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                continue

        logger.warning(f"Could not parse calendar date: {date_str}")
        return None
