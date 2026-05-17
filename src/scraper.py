import logging
from typing import Dict, List
from src.utils import http_get, http_post, save_json, create_data_directories
from src.parsers.sisu_parser import SisuParser
from src.parsers.chiller_parser import ChillerParser
from src.comparator import GapAnalyzer
from config import SISU_URL, CHILLER_URL, CHILLER_BODY, get_dated_data_dir

logger = logging.getLogger(__name__)


class ScheduleScraper:
    def __init__(self):
        self.sisu_parser = SisuParser(SISU_URL)
        self.data_dir = None
        self.teams_dir = None
        self.results = {
            "teams": [],
            "failed_teams": [],
            "chiller_schedule": None,
            "chiller_failed": False,
            "gap_analysis": None
        }

    def scrape_all(self) -> Dict:
        """
        Main entry point: scrape Sisu teams, Chiller rink schedule, and analyze gaps.
        """
        # Initialize dated data directories
        self.data_dir = get_dated_data_dir()
        create_data_directories(self.data_dir)
        self.teams_dir = self.data_dir + "/teams"

        logger.info("Starting schedule scrape...")
        logger.info(f"Sisu URL: {SISU_URL}")
        logger.info(f"Chiller URL: {CHILLER_URL}")
        logger.info(f"Data directory: {self.data_dir}")

        # Scrape Sisu Thunderbirds
        self._scrape_sisu_teams()

        # Scrape The Chiller rink schedule
        self._scrape_chiller()

        # Analyze gaps
        self._analyze_gaps()

        logger.info(f"Scraping complete. Teams: {len(self.results['teams'])}, "
                    f"Failed: {len(self.results['failed_teams'])}")
        return self.results

    def _scrape_sisu_teams(self) -> None:
        """
        Fetch Sisu homepage, find team links from Teams menu, and scrape each team's calendar.
        """
        logger.info("Fetching Sisu Thunderbirds homepage...")
        homepage_html = http_get(SISU_URL)

        if not homepage_html:
            logger.error("Failed to fetch Sisu homepage")
            return

        logger.info("Parsing team links from Teams menu...")
        teams = self.sisu_parser.fetch_teams(homepage_html)

        if not teams:
            logger.error("No teams found in Teams menu")
            return

        logger.info(f"Found {len(teams)} teams to scrape")

        for team_name, calendar_url in teams:
            self._scrape_team_calendar(team_name, calendar_url)

    def _scrape_team_calendar(self, team_name: str, calendar_url: str) -> None:
        """
        Scrape a team's calendar page.
        """
        logger.info(f"Scraping {team_name} calendar from {calendar_url}...")

        calendar_html = http_get(calendar_url)
        if not calendar_html:
            logger.error(f"Failed to fetch calendar for {team_name}")
            self.results["failed_teams"].append(team_name)
            return

        # Parse the calendar
        events = self.sisu_parser.parse_calendar(calendar_html, team_name)

        # Create team data structure
        team_data = {
            "team_name": team_name,
            "calendar_url": calendar_url,
            "events": events,
            "event_count": len(events)
        }

        # Save to JSON file
        filename = self._sanitize_filename(team_name) + ".json"
        try:
            save_json(filename, team_data, self.teams_dir)
            self.results["teams"].append(team_name)
            logger.info(f"Successfully saved {team_name} calendar ({len(events)} events)")
        except Exception as e:
            logger.error(f"Error saving {team_name} calendar: {e}")
            self.results["failed_teams"].append(team_name)

    def _scrape_chiller(self) -> None:
        """
        POST to The Chiller API to get rink schedule.
        """
        logger.info("Fetching Chiller rink schedule...")

        response = http_post(CHILLER_URL, CHILLER_BODY, headers={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        if not response:
            logger.error("Failed to fetch Chiller rink schedule")
            self.results["chiller_failed"] = True
            return

        # Parse the response
        try:
            schedule_data = ChillerParser.parse_schedule(response)
            if not schedule_data:
                logger.error("Failed to parse Chiller response")
                self.results["chiller_failed"] = True
                return

            # Normalize the data
            normalized = ChillerParser.normalize_schedule(schedule_data)

            # Save to JSON file
            save_json("rink_schedule.json", normalized, self.data_dir)
            self.results["chiller_schedule"] = normalized
            logger.info(f"Successfully saved Chiller rink schedule")
        except Exception as e:
            logger.error(f"Error processing Chiller schedule: {e}")
            self.results["chiller_failed"] = True

    def _analyze_gaps(self) -> None:
        """
        Analyze gaps between team schedules and rink schedule.
        """
        logger.info("Analyzing gaps between team and rink schedules...")

        try:
            analyzer = GapAnalyzer(self.data_dir)
            gap_report = analyzer.analyze()

            # Save gap report
            save_json("gap_analysis.json", gap_report, self.data_dir)
            self.results["gap_analysis"] = gap_report
            logger.info("Gap analysis complete and saved")
        except Exception as e:
            logger.error(f"Error during gap analysis: {e}")

    @staticmethod
    def _sanitize_filename(team_name: str) -> str:
        """Convert team name to safe filename."""
        import re
        # Replace spaces and special characters
        safe_name = re.sub(r'[^\w\s-]', '', team_name)
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        return safe_name.lower()

    def print_summary(self) -> None:
        """Print summary of scraping results."""
        print("\n" + "="*60)
        print("SCHEDULE SCRAPING SUMMARY")
        print("="*60)
        print(f"Data saved to: {self.data_dir}")
        print(f"\nSuccessfully scraped: {len(self.results['teams'])} teams")
        for team in self.results['teams']:
            print(f"  ✓ {team}")
        if self.results['failed_teams']:
            print(f"\nFailed to scrape: {len(self.results['failed_teams'])} teams")
            for team in self.results['failed_teams']:
                print(f"  ✗ {team}")
        if self.results['chiller_schedule']:
            print(f"\n✓ Rink schedule downloaded successfully")
        elif self.results['chiller_failed']:
            print(f"\n✗ Failed to download rink schedule")

        # Print gap analysis summary
        if self.results['gap_analysis']:
            gap_report = self.results['gap_analysis']
            summary = gap_report['summary']
            print(f"\n✓ Gap analysis complete")
            print(f"  Total team events: {summary['total_team_events']}")
            print(f"  Events at Chiller rinks: {summary['events_at_chiller_rinks']}")
            print(f"  Events not in rink schedule: {summary['events_not_in_rink_schedule']}")
            print(f"  Coverage: {summary['coverage_percentage']}%")
        print("="*60 + "\n")
