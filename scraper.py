import requests
import json
import time
import schedule
from datetime import datetime
import os
import re

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
                
                if 'News' in data and isinstance(data['News'], list):
                    news_items = data['News']
                    
                    new_items = 0
                    for item in news_items:
                        # Check if the item has the 'active-critical' level
                        level = item.get('Level', '')
                        if 'active-critical' in level:
                            headline_text = item.get('Title', '')
                            time_text = item.get('PostedLong', '')
                            
                            # Create headline object
                            headline_data = {
                                "headline": headline_text,
                                "time": time_text,
                                "level": level,
                                "labels": item.get('Labels', []),
                                "news_id": item.get('NewsID', ''),
                                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            # Check if this headline is already in our data
                            if not any(h['news_id'] == headline_data['news_id'] for h in self.headlines):
                                self.headlines.append(headline_data)
                                new_items += 1
                                print(f"New critical headline: {headline_text}")
                    
                    print(f"Found {new_items} new critical headlines")
                else:
                    print("Unexpected API response format - 'd' key not found")
                    print(f"Response contains keys: {list(data.keys())}")
            
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                print(f"Raw response: {response.text[:200]}...")  # Print first 200 chars
            
            self.save_data()
            
        except Exception as e:
            print(f"Error during scraping: {e}")
    
    def save_data(self):
        """Save the headlines data to the JSON file"""
        with open(self.output_file, 'w') as f:
            json.dump(self.headlines, f, indent=2)
        print(f"Data saved to {self.output_file}")
    
    def start_scheduled_scraping(self, interval_minutes=5):
        """Schedule the scraping to run at fixed intervals during trading hours"""
        schedule.every(interval_minutes).minutes.do(self.run_if_trading_hours)
        
        print(f"Scraper scheduled to run every {interval_minutes} minutes during trading hours")
        print("Press Ctrl+C to exit")
        
        # Run once immediately
        self.scrape()
        
        # Keep the script running
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    def run_if_trading_hours(self):
        """Only run the scraper during trading hours"""
        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour
        
        # Trading hours: Monday to Friday, 9:30 AM to 4:00 PM
        if 0 <= weekday <= 4 and 9 <= hour < 16:
            # If it's between 9:30 and 4:00
            if hour == 9 and now.minute < 30:
                return  # Before market open
            self.scrape()
        else:
            print(f"Outside trading hours, skipping scrape at {now.strftime('%H:%M:%S')}")


if __name__ == "__main__":
    api_url = "https://live.financialjuice.com/FJService.asmx/Startup?info=%22EAAAAAV5Ztc%2Bltam62cRcX71rohbT3%2FNWmgAuMUGG1Z0MVXB7dk3%2Fi6NdikIbC%2BhMngX4kJQZrPcPFOAnR%2Bfvqrufncxy7zn7nLD1dGxju1HllhWLR3bYZDnPOzYSz7Ls0iOfQOzOTjzisYuiUdPtaBclkdeuCF7fa869owcXMV2osub%2Fg%2FiePe%2FhMIOQhnaaIh%2BR3MLtRrmOh%2BCHmcLT22c1e7Y4OqcQa6wQyQ1NYEX3mu0j8KwQW1gQELcG83ywyCGoKDzB%2BZOXiq%2ByUBaKvGyf0EFaWj8j95Hi4NSAtzZlIrrakPj60ZyEFN7Q1x0fo5rNA%3D%3D%22&TimeOffset=5.5&tabID=0&oldID=0&TickerID=0&FeedCompanyID=0&strSearch=&extraNID=0"
    
    scraper = FinJuiceNewsScraper(api_url)
    
    # Set the interval in minutes (e.g., 5 minutes)
    scraper.start_scheduled_scraping(interval_minutes=5)