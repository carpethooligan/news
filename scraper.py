import requests
import json
import time
import schedule
from datetime import datetime
import os
import re
from dateutil import parser
import pandas as pd

class FinJuiceScraper:
    def __init__(self):
        # Headers to mimic browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.5',
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive',
            'Referer': 'https://www.financialjuice.com/'
        }
        self.headlines = []
        self.events = []
        self.news_api_url = None
        self.news_output_file = None
        self.events_api_url = None
        self.events_output_file = None

    def init_news_scraper(self, api_url, output_file="critical_headlines.json"):
        self.news_api_url = api_url
        self.news_output_file = output_file
        
        # Load existing data if file exists
        if os.path.exists(self.news_output_file):
            try:
                with open(self.news_output_file, 'r') as f:
                    self.headlines = json.load(f)
            except json.JSONDecodeError:
                print(f"Error reading {self.news_output_file}, starting with empty data")
                self.headlines = []

    def init_events_scraper(self, api_url, output_file="events.json"):
        self.events_api_url = api_url
        self.events_output_file = output_file

    def get_api_response(self, api_url):
        """Get response from API"""
        print(f"Requesting API at {datetime.now().strftime('%H:%M:%S')}")
        response = requests.get(api_url, headers=self.headers)
        if response.status_code != 200:
            print(f"Failed to fetch content: Status code {response.status_code}")
            return None
        
        # Save response text to a file - ONLY FOR DEBUGGING
        # with open('response_data.txt', 'w', encoding='utf-8') as f:
        #     f.write(response.text)
        
        print(f"Response length: {len(response.text)} characters")
        return response.text

    def extract_json_from_response(self, response_text):
        """Extract JSON data from between string tags"""
        try:
            # Look for JSON between string tags, ignoring whitespace
            match = re.search(r'<string[^>]*>(.*)</string>', response_text, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            else:
                print("No JSON found between string tags")
                return None
        except Exception as e:
            print(f"Error extracting JSON: {e}")
            print("Full response:")
            print(response_text)
            return None

    def scrape_news(self):
        """Scrape news headlines"""
        print(f"Running news scrape at {datetime.now().strftime('%H:%M:%S')}")
        try:
            response_text = self.get_api_response(self.news_api_url)
            if not response_text:
                return
            
            data = self.extract_json_from_response(response_text)
            if not data:
                return
            
            for item in data:
                level = item.get("Level")
                if not ('active-critical' in level and 'active' in level):
                    continue

                headline_data = {
                    "headline": item.get("Title"),
                    "time": item.get("PostedLong") or (item.get("Date") + " " + item.get("Time")),
                    "level": level,
                    "labels": item.get("Labels"),
                    "news_id": item.get("NewsID") or item.get("ID"),
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                self.headlines.append(headline_data)

            print(f"Found {len(self.headlines)} new critical headlines")
            self.save_news_data()
            self.headlines = []
            
        except Exception as e:
            print(f"Error during news scraping: {e}")

    def scrape_events(self):
        """Scrape events data"""
        print(f"Running events scrape at {datetime.now().strftime('%H:%M:%S')}")
        try:
            response_text = self.get_api_response(self.events_api_url)
            if not response_text:
                return
            
            data = self.extract_json_from_response(response_text)
            if not data:
                return
            
            if 'Cal' not in data or not isinstance(data['Cal'], list):
                print("No 'Cal' section found in API response")
                return
            
            df = pd.DataFrame(data['Cal'])
            # df.columns

            df['datetime'] = pd.to_datetime(df['Date'], errors='coerce')

            # For TESTING ONLY
            # target_date = "2025-05-05"
            # target_date = pd.to_datetime(target_date).normalize()
            
            # Use today's date
            target_date = pd.Timestamp.today().normalize()
            df = df[df['datetime'].dt.normalize() == target_date]

            # Keep only relevant fields
            fields = ["Date", "Time", "RealDate", "Title", "Active", "Breaking", "Actual", "Forecast", "Previous"]
            df = df[fields].copy()

            self.events = df.to_dict(orient="records")
            self.save_events_data(target_date.date())
            
        except Exception as e:
            print(f"Error during events scraping: {e}")
    
    def save_news_data(self):
        """Save the headlines data to the JSON file"""
        if not self.headlines:
            return
            
        try:
            # Get current time
            current_time = datetime.now()
            
            # Filter headlines less than 5 minutes old
            recent_headlines = []
            for headline in self.headlines:
                try:
                    headline_time = parser.parse(headline['time'])
                    time_diff = (current_time - headline_time).total_seconds() / 60
                    if time_diff < 5:
                        recent_headlines.append(headline)
                except (ValueError, KeyError) as e:
                    print(f"Error parsing time for headline: {e}")
                    continue
            
            if not recent_headlines:
                return
                
            # Save only recent headlines
            with open(self.news_output_file, 'w') as f:
                json.dump(recent_headlines, f, indent=2)
            print(f"News data saved to {self.news_output_file}")
        except Exception as e:
            print(f"Error saving news data: {e}")
    
    def save_events_data(self, target_date):
        """Save the events data to the JSON file"""
        if not self.events:
            return
        
        output_file = f"{target_date}_{self.events_output_file}"
        
        try:
            with open(output_file, 'w') as f:
                json.dump(self.events, f, indent=2)
            print(f"Events data saved to {output_file}")
        except Exception as e:
            print(f"Error saving events data: {e}")
    
    def start_scheduled_scraping(self, interval_minutes=5):
        """Schedule the scraping to run at fixed intervals"""
        schedule.every(interval_minutes).minutes.do(self.run_if_trading_hours)
        
        print(f"Scraper scheduled to run every {interval_minutes} minutes")
        print("Press Ctrl+C to exit")
        
        # Run once immediately
        self.scrape_news()
        
        # Sceduled events can be retrieved at SOD; no need to schedule them
        self.scrape_events()
        
        # Keep the script running
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    def run_if_trading_hours(self):
        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour
        
        # Trading hours: Monday to Friday, 9:30 AM to 4:00 PM
        if 0 <= weekday <= 4 and 8 <= hour < 16:       
            self.scrape_news()
        else:
            print(f"Outside trading hours, skipping scrape at {now.strftime('%H:%M:%S')}")


if __name__ == "__main__":
    news_api_url = "https://live.financialjuice.com/FJService.asmx/GetPreviousNews?info=%22EAAAAEoNUlDjJhC%2B8QQZMqAtYlv9wI5hj3cJUEZnwJZlfh3lTQtDxaq7HAZDxqjkhtO6ExQGZijYR9NyXGZ%2F0UE3ziMMYzCRkXyVqugDJhR5D%2BfSsScg0lFWkv2r4IpGRZHGFfLxK6a%2FIYJH6r6zE7X3tyl0VvPUXpZOharrstvWNIE0kjXGwHmQrEq5U%2BhfpZz7Le2G4SwjDgtH2I%2BBL%2BnUjKXrGrshl1dlY9SZEXU7zvx%2BYOjDTciC23PlI%2Bl55PdBZjQ9UEr7su235bAJqmQz0LJEzMtnnF%2FR8gPU%2FI5SFB2i5ULrYwQov0yJtLZv4WGZBA%3D%3D%22&TimeOffset=-4&tabID=10&oldID=0&TickerID=0&FeedCompanyID=0&strSearch=%22%22&extraNID=0"
    events_api_url = "https://live.financialjuice.com/FJService.asmx/Startup?info=%22EAAAAAV5Ztc%2Bltam62cRcX71rohbT3%2FNWmgAuMUGG1Z0MVXB7dk3%2Fi6NdikIbC%2BhMngX4kJQZrPcPFOAnR%2Bfvqrufncxy7zn7nLD1dGxju1HllhWLR3bYZDnPOzYSz7Ls0iOfQOzOTjzisYuiUdPtaBclkdeuCF7fa869owcXMV2osub%2Fg%2FiePe%2FhMIOQhnaaIh%2BR3MLtRrmOh%2BCHmcLT22c1e7Y4OqcQa6wQyQ1NYEX3mu0j8KwQW1gQELcG83ywyCGoKDzB%2BZOXiq%2ByUBaKvGyf0EFaWj8j95Hi4NSAtzZlIrrakPj60ZyEFN7Q1x0fo5rNA%3D%3D%22&TimeOffset=5.5&tabID=0&oldID=0&TickerID=0&FeedCompanyID=0&strSearch=&extraNID=0"
    
    scraper = FinJuiceScraper()
    scraper.init_news_scraper(news_api_url)
    scraper.init_events_scraper(events_api_url)
    
    # Set the interval in minutes (e.g., 5 minutes)
    scraper.start_scheduled_scraping(interval_minutes=1)