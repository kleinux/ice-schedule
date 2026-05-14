#!/usr/bin/env python3

import sys
import logging
from src.scraper import ScheduleScraper
import config

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the schedule scraper."""
    try:
        logger.info("Starting Ice Schedule Scraper")
        scraper = ScheduleScraper()
        results = scraper.scrape_all()
        scraper.print_summary()

        # Return success/failure based on results
        if results['teams'] or not results['chiller_failed']:
            return 0
        else:
            return 1

    except Exception as e:
        logger.error(f"Fatal error during scraping: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
