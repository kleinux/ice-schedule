import logging
import os
import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

CHILLER_RINKS = {
    'North 1', 'North 2', 'North 3',
    'Dublin 1', 'Dublin 2',
    'Fairgrounds', 'Ice Haus', 'Ice Works'
}


class GapAnalyzer:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.teams_dir = os.path.join(data_dir, 'teams')
        self.team_events = []
        self.rink_events = []
        self.gaps = []

    def analyze(self) -> Dict:
        """Run complete gap analysis and return report."""
        logger.info("Starting gap analysis...")

        self._load_all_schedules()
        self._find_gaps()
        report = self._generate_report()

        logger.info(f"Gap analysis complete. Found {len(self.gaps)} gaps.")
        return report

    def _load_all_schedules(self) -> None:
        """Load all team and rink schedules into memory."""
        logger.info("Loading all schedules...")

        # Load rink schedule
        rink_file = os.path.join(self.data_dir, 'rink_schedule.json')
        if os.path.exists(rink_file):
            with open(rink_file, 'r') as f:
                rink_data = json.load(f)
            if 'data' in rink_data and 'aaData' in rink_data['data']:
                self.rink_events = rink_data['data']['aaData']
                logger.info(f"Loaded {len(self.rink_events)} rink events")

        # Load team schedules
        if os.path.exists(self.teams_dir):
            for filename in os.listdir(self.teams_dir):
                if filename.endswith('.json'):
                    team_file = os.path.join(self.teams_dir, filename)
                    try:
                        with open(team_file, 'r') as f:
                            team_data = json.load(f)
                        for event in team_data.get('events', []):
                            event['team'] = team_data.get('team_name', 'Unknown')
                            self.team_events.append(event)
                        logger.debug(f"Loaded {len(team_data.get('events', []))} events from {team_data.get('team_name')}")
                    except Exception as e:
                        logger.error(f"Error loading {filename}: {e}")

        logger.info(f"Loaded total {len(self.team_events)} team events from {len(os.listdir(self.teams_dir) if os.path.exists(self.teams_dir) else 0)} teams")

    def _find_gaps(self) -> None:
        """Compare team events to rink schedule and find gaps."""
        logger.info("Finding gaps in schedule...")

        for team_event in self.team_events:
            # Skip events not at Chiller rinks
            location = team_event.get('location', '').strip()
            if not location or location not in CHILLER_RINKS:
                logger.debug(f"Skipping {team_event.get('team')} event at {location} (not a Chiller rink)")
                continue

            # Try to find matching rink event
            if not self._find_matching_rink_event(team_event):
                self.gaps.append(team_event)
                logger.debug(f"Found gap: {team_event.get('team')} on {team_event.get('date')} at {location}")

    def _find_matching_rink_event(self, team_event: Dict) -> bool:
        """
        Check if team event has a matching rink schedule entry.
        Returns True if match found, False otherwise.
        """
        team_date = team_event.get('date')  # ISO format: 2026-06-01
        team_location = team_event.get('location')
        team_time = team_event.get('time')  # format: "6:00 PM(1h)"

        if not team_date or not team_location or not team_time:
            return False

        # Extract hour from team time (e.g., "6" from "6:00 PM(1h)")
        team_hour = self._extract_hour(team_time)

        # Convert ISO date to rink format (2026-06-01 -> 6/1/2026)
        rink_date = self._convert_date_to_rink_format(team_date)

        # Search rink events for match
        for rink_event in self.rink_events:
            if rink_event.get('Date') != rink_date:
                continue
            if rink_event.get('Rink') != team_location:
                continue

            # Check if times match (same hour)
            rink_hour = self._extract_hour_from_rink_time(rink_event.get('StartTime', ''))
            if rink_hour == team_hour:
                logger.debug(f"Found match for {team_event.get('team')} on {team_date}: {rink_event.get('Event')}")
                return True

        return False

    @staticmethod
    def _extract_hour(time_str: str) -> Optional[int]:
        """Extract hour from time string like '6:00 PM(1h)' or '6:00 AM'."""
        if not time_str:
            return None
        try:
            # Remove duration info if present
            time_str = time_str.split('(')[0].strip()
            # Parse time with AM/PM
            time_obj = datetime.strptime(time_str, '%I:%M %p')
            return time_obj.hour
        except ValueError:
            logger.warning(f"Could not parse time: {time_str}")
            return None

    @staticmethod
    def _extract_hour_from_rink_time(time_str: str) -> Optional[int]:
        """Extract hour from rink time string like '6:00 AM' or '6:00 PM'."""
        if not time_str:
            return None
        try:
            time_obj = datetime.strptime(time_str.strip(), '%I:%M %p')
            return time_obj.hour
        except ValueError:
            logger.warning(f"Could not parse rink time: {time_str}")
            return None

    @staticmethod
    def _convert_date_to_rink_format(iso_date: str) -> str:
        """Convert ISO date (2026-06-01) to rink format (6/1/2026)."""
        try:
            date_obj = datetime.strptime(iso_date, '%Y-%m-%d')
            return date_obj.strftime('%-m/%-d/%Y') if os.name != 'nt' else date_obj.strftime('%#m/%#d/%Y')
        except ValueError:
            logger.warning(f"Could not convert date: {iso_date}")
            return iso_date

    def _generate_report(self) -> Dict:
        """Generate gap analysis report."""
        # Count events at Chiller rinks
        events_at_chiller = sum(
            1 for event in self.team_events
            if event.get('location', '').strip() in CHILLER_RINKS
        )

        total_events = len(self.team_events)
        gaps_count = len(self.gaps)
        coverage = (events_at_chiller - gaps_count) / events_at_chiller * 100 if events_at_chiller > 0 else 0

        report = {
            "summary": {
                "total_team_events": total_events,
                "events_at_chiller_rinks": events_at_chiller,
                "events_not_in_rink_schedule": gaps_count,
                "coverage_percentage": round(coverage, 1)
            },
            "gaps": self.gaps
        }

        return report
