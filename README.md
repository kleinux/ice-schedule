# ice-schedule

An automated schedule scraper for SISU Thunderbirds hockey teams and The Chiller rink schedules.

## Overview

This application downloads and consolidates hockey schedules from two sources:

1. **SISU Thunderbirds** (https://www.sisuthunderbirds.com/) - Individual team schedules
2. **The Chiller** (https://www.thechiller.com/) - Rink-wide event scheduling

The scraped data is saved as JSON files in the `data/` directory for easy access and further processing.

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository
2. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Usage

Run the scraper:

```bash
python3 main.py
```

The script will:
- Connect to the SISU Thunderbirds website and find all team schedule links
- Scrape each team's schedule data
- Download the rink schedule from The Chiller
- Save all data as JSON files in the `data/` directory

## Output

### Directory Structure

```
data/
├── teams/
│   ├── team1.json
│   ├── team2.json
│   └── ...
└── rink_schedule.json
```

### Team Schedule Format

Each team gets a JSON file with the following structure:

```json
{
  "team_name": "Team Name",
  "team_url": "https://...",
  "schedule": [
    {
      "date": "2026-05-13",
      "time": "19:30",
      "opponent": "Opponent Name",
      "location": "Venue Name",
      "game_type": "Home",
      "status": "Scheduled"
    }
  ],
  "game_count": 1
}
```

### Rink Schedule Format

The rink schedule is saved as `rink_schedule.json` with comprehensive facility scheduling information from The Chiller.

## Project Structure

```
.
├── main.py                    # Entry point
├── config.py                  # Configuration constants
├── requirements.txt           # Python dependencies
├── src/
│   ├── scraper.py            # Main scraping orchestration
│   ├── utils.py              # HTTP requests, file I/O, logging
│   └── parsers/
│       ├── sisu_parser.py     # SISU team page parsing
│       └── chiller_parser.py  # Chiller API response parsing
└── data/                      # Generated output (ignored by git)
```

## Error Handling

- The scraper includes automatic retry logic (3 attempts) for failed HTTP requests
- If a team's schedule fails to download, the error is logged and scraping continues with other teams
- A summary is printed at the end showing successful and failed scrapes

## Logging

The application logs to the console with timestamps and log levels. Output shows:
- Progress of team discovery and scraping
- Any errors or warnings encountered
- Summary of results

## Notes

- The scraper respects website resources with reasonable timeouts and retry delays
- User-Agent header is set to identify the scraper appropriately
- Output data is formatted as pretty-printed JSON for readability