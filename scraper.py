import requests
import json
import time
import schedule
from datetime import datetime
import os
import re
from dateutil import parser

class FinJuiceNewsScraper:
    def __init__(self, api_url, output_file="critical_headlines.json"):
        self.api_url = api_url
        self.output_file = output_file
        self.headlines = []
        # Headers to mimic browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.5',
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive',
            'Referer': 'https://www.financialjuice.com/'
        }
        
        # Load existing data if file exists
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r') as f:
                    self.headlines = json.load(f)
            except json.JSONDecodeError:
                print(f"Error reading {self.output_file}, starting with empty data")
                self.headlines = []

    def scrape(self):
        print(f"Running API scrape at {datetime.now().strftime('%H:%M:%S')}")
        try:
            response = requests.get(self.api_url, headers=self.headers)
            if response.status_code != 200:
                print(f"Failed to fetch content: Status code {response.status_code}")
                return
            
            # Parse the response
            try:
                # The response is a complete XML document with XML declaration and possible whitespace
                response_text = response.text
                
                # Save response text to a file - ONLY FOR DEBUGGING
                # with open('response_data.txt', 'w', encoding='utf-8') as f:
                #     f.write(response_text)
               
                print(f"Response length: {len(response_text)} characters")
                
                try:
                    # Look for JSON between string tags, ignoring whitespace
                    match = re.search(r'<string[^>]*>(.*)</string>', response_text, re.DOTALL)
                    if match:
                        json_str = match.group(1)
                        data = json.loads(json_str)
                except Exception as e:
                    print(f"Regex extraction failed: {e}")
                    print("Full response:")
                    print(response_text)
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
               
            
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                print(f"Raw response: {response.text[:200]}...")  # Print first 200 chars
            
            self.save_data()
            self.headlines = []
            
        except Exception as e:
            print(f"Error during scraping: {e}")
    
    def save_data(self):
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
            with open(self.output_file, 'w') as f:
                json.dump(recent_headlines, f, indent=2)
            print(f"Data saved to {self.output_file}")
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def start_scheduled_scraping(self, interval_minutes=5):
        """Schedule the scraping to run at fixed intervals"""
        schedule.every(interval_minutes).minutes.do(self.run_if_trading_hours)
        
        print(f"Scraper scheduled to run every {interval_minutes} minutes")
        print("Press Ctrl+C to exit")
        
        # Run once immediately
        self.scrape()
        
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
            self.scrape()
        else:
            print(f"Outside trading hours, skipping scrape at {now.strftime('%H:%M:%S')}")


if __name__ == "__main__":
    api_url = "https://live.financialjuice.com/FJService.asmx/GetPreviousNews?info=%22EAAAAEoNUlDjJhC%2B8QQZMqAtYlv9wI5hj3cJUEZnwJZlfh3lTQtDxaq7HAZDxqjkhtO6ExQGZijYR9NyXGZ%2F0UE3ziMMYzCRkXyVqugDJhR5D%2BfSsScg0lFWkv2r4IpGRZHGFfLxK6a%2FIYJH6r6zE7X3tyl0VvPUXpZOharrstvWNIE0kjXGwHmQrEq5U%2BhfpZz7Le2G4SwjDgtH2I%2BBL%2BnUjKXrGrshl1dlY9SZEXU7zvx%2BYOjDTciC23PlI%2Bl55PdBZjQ9UEr7su235bAJqmQz0LJEzMtnnF%2FR8gPU%2FI5SFB2i5ULrYwQov0yJtLZv4WGZBA%3D%3D%22&TimeOffset=-4&tabID=10&oldID=0&TickerID=0&FeedCompanyID=0&strSearch=%22%22&extraNID=0"
    
    scraper = FinJuiceNewsScraper(api_url)
    
    # Set the interval in minutes (e.g., 5 minutes)
    scraper.start_scheduled_scraping(interval_minutes=1)