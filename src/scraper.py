import logging
from typing import Dict, List
from src.utils import http_get, http_post, save_json, create_data_directories
from src.parsers.sisu_parser import SisuParser
from src.parsers.chiller_parser import ChillerParser
from config import SISU_URL, CHILLER_URL, TEAMS_DIR

logger = logging.getLogger(__name__)


class ScheduleScraper:
    def __init__(self):
        self.sisu_parser = SisuParser(SISU_URL)
        self.results = {
            "teams": [],
            "failed_teams": [],
            "chiller_schedule": None,
            "chiller_failed": False
        }

    def scrape_all(self) -> Dict:
        """
        Main entry point: scrape Sisu teams and Chiller rink schedule.
        """
        create_data_directories()

        logger.info("Starting schedule scrape...")
        logger.info(f"Sisu URL: {SISU_URL}")
        logger.info(f"Chiller URL: {CHILLER_URL}")

        # Scrape Sisu Thunderbirds
        self._scrape_sisu_teams()

        # Scrape The Chiller rink schedule
        self._scrape_chiller()

        logger.info(f"Scraping complete. Teams: {len(self.results['teams'])}, "
                    f"Failed: {len(self.results['failed_teams'])}")
        return self.results

    def _scrape_sisu_teams(self) -> None:
        """
        Fetch Sisu homepage, find team links, and scrape each team's schedule.
        """
        logger.info("Fetching Sisu Thunderbirds homepage...")
        homepage_html = http_get(SISU_URL)

        if not homepage_html:
            logger.error("Failed to fetch Sisu homepage")
            return

        logger.info("Parsing team links from homepage...")
        teams = self.sisu_parser.fetch_teams(homepage_html)

        if not teams:
            logger.error("No teams found on Sisu homepage")
            return

        logger.info(f"Found {len(teams)} teams to scrape")

        for team_name, team_url in teams:
            self._scrape_team(team_name, team_url)

    def _scrape_team(self, team_name: str, team_url: str) -> None:
        """
        Scrape schedule for a single team.
        """
        logger.info(f"Scraping {team_name} from {team_url}...")

        team_html = http_get(team_url)
        if not team_html:
            logger.error(f"Failed to fetch schedule for {team_name}")
            self.results["failed_teams"].append(team_name)
            return

        # Parse the schedule
        schedule = self.sisu_parser.parse_schedule(team_html, team_name)

        # Create team data structure
        team_data = {
            "team_name": team_name,
            "team_url": team_url,
            "schedule": schedule,
            "game_count": len(schedule)
        }

        # Save to JSON file
        filename = self._sanitize_filename(team_name) + ".json"
        try:
            save_json(filename, team_data, TEAMS_DIR)
            self.results["teams"].append(team_name)
            logger.info(f"Successfully saved {team_name} schedule ({len(schedule)} games)")
        except Exception as e:
            logger.error(f"Error saving {team_name} schedule: {e}")
            self.results["failed_teams"].append(team_name)

    def _scrape_chiller(self) -> None:
        """
        POST to The Chiller API to get rink schedule.
        """
        logger.info("Fetching Chiller rink schedule...")

        response = http_post(CHILLER_URL)
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
            save_json("rink_schedule.json", normalized)
            self.results["chiller_schedule"] = normalized
            logger.info(f"Successfully saved Chiller rink schedule")
        except Exception as e:
            logger.error(f"Error processing Chiller schedule: {e}")
            self.results["chiller_failed"] = True

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
        print(f"Successfully scraped: {len(self.results['teams'])} teams")
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
        print("="*60 + "\n")
