# Financial Juice Critical News Scraper

A Python utility that scrapes critical market news headlines from the Financial Juice website (https://www.financialjuice.com/).

## Overview

This scraper targets the "active-critical" headlines (red highlighted breaking news) from Financial Juice by directly accessing their API endpoint. It extracts and saves these important market-moving news items with timestamps and additional metadata.

## Features

- Directly interfaces with the Financial Juice API endpoint
- Extracts "active-critical" news items from XML-wrapped JSON responses
- Saves detailed news information to a JSON file including:
  - Headline text
  - Timestamp
  - News level/priority
  - Labels
  - Unique news ID
  - Scrape timestamp
- Avoids duplicate entries by tracking news IDs
- Includes scheduled scraping during market hours (Monday-Friday, 8 AM - 4:00 PM)
- Customizable scraping interval (default: every 5 minutes)

## Requirements

- Python 3.x
- Required packages:
  - requests
  - schedule
  - json, time, datetime, os, re (standard library)

## Usage

Simply run the script to begin scraping:

```
python scraper.py
```

The scraper will:
1. Run immediately upon execution
2. Continue to execute at the specified interval (default: 5 minutes) during market hours
3. Save results to `critical_headlines.json` in the same directory

## Configuration

You can modify the following parameters in the script:
- `output_file`: Change the output JSON filename
- `interval_minutes`: Adjust the frequency of scraping
- `api_url`: Update if the API endpoint changes

## Output Format

The script generates a JSON file with an array of headline objects:

```json
[
  {
    "headline": "Breaking news headline text",
    "time": "Posted time from source",
    "level": "active-critical",
    "labels": ["Label1", "Label2"],
    "news_id": "unique-id",
    "scraped_at": "2023-05-10 14:30:45"
  },
  ...
]
``` 
