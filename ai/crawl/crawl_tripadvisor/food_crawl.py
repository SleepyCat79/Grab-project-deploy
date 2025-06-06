#!/usr/bin/env python3
"""
Enhanced TripAdvisor Restaurant Crawler
A specialized crawler that extracts clean, structured restaurant details from TripAdvisor.
Adapted from the attractions crawler (patch.py)
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
import random
import re
import logging
from urllib.parse import urljoin
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from datetime import datetime

import nest_asyncio
nest_asyncio.apply()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("restaurant_crawler.log")
    ]
)
logger = logging.getLogger(__name__)


class RestaurantCrawler:
    """Crawler for TripAdvisor restaurants with detailed data extraction"""

    def __init__(self, base_url=None, delay=3.0, custom_type=None, save_interval=15):
        self.base_url = base_url or "https://www.tripadvisor.com/FindRestaurants?geo=293925&establishmentTypes=10591%2C11776%2C16548%2C16556%2C21908%2C9900%2C9901%2C9909&broadened=false"
        self.min_delay = delay
        self.max_delay = delay * 2
        self.save_interval = save_interval
        self.last_save_time = time.time()
        self.headers = {
            'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/123.0.0.0 Safari/537.36'),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://www.tripadvisor.com/'
        }
        self.visited_urls = self.load_visited_urls()
        self.visited_restaurants = set()
        self.custom_type = custom_type
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.master_data = self.load_master_data()

    def load_visited_urls(self):
        """Load previously visited URLs from file"""
        visited_file = "visited_urls.json"
        try:
            if os.path.exists(visited_file):
                with open(visited_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
        except Exception as e:
            logger.error(f"Error loading visited URLs: {str(e)}")
        return set()

    def save_visited_urls(self):
        """Save visited URLs to file"""
        visited_file = "visited_urls.json"
        try:
            with open(visited_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.visited_urls), f, indent=2)
            logger.info(f"Saved {len(self.visited_urls)} visited URLs")
        except Exception as e:
            logger.error(f"Error saving visited URLs: {str(e)}")

    def _random_delay(self):
        """Add a random delay between requests to avoid being blocked"""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.info(f"Waiting for {delay:.2f} seconds")
        time.sleep(delay)

    def _should_save(self):
        """Check if it's time to save data"""
        minutes_since_last_save = (time.time() - self.last_save_time) / 60
        return minutes_since_last_save >= self.save_interval

    def load_master_data(self):
        """Load all previously crawled restaurants from master file"""
        master_file = "all_restaurants.json"
        try:
            if os.path.exists(master_file):
                with open(master_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data)} restaurants from master file")
                    return data
        except Exception as e:
            logger.error(f"Error loading master data: {str(e)}")
        return []

    def save_master_data(self, new_data):
        """Save all restaurants to master file, avoiding duplicates"""
        master_file = "all_restaurants.json"
        try:
            # Merge new data with existing master data
            all_data = self.master_data + new_data
            
            # Remove duplicates based on URL while keeping the newest data
            url_to_data = {}
            for item in all_data:
                url_to_data[item['url']] = item
            
            unique_data = list(url_to_data.values())
            
            # Save to master file
            with open(master_file, 'w', encoding='utf-8') as f:
                json.dump(unique_data, f, indent=2, ensure_ascii=False)
            
            # Update master data in memory
            self.master_data = unique_data
            
            logger.info(f"Saved {len(unique_data)} restaurants to master file")
            
            # Create a backup of master file
            backup_file = f"all_restaurants_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(unique_data, f, indent=2, ensure_ascii=False)
            
            # Keep only the last 5 backups
            backup_files = sorted([f for f in os.listdir('.') if f.startswith('all_restaurants_backup_')])
            for old_backup in backup_files[:-5]:
                os.remove(old_backup)
                
        except Exception as e:
            logger.error(f"Error saving master data: {str(e)}")

    def save_data(self, data, output_dir, location):
        """Save data to file with date-based organization and master file"""
        if not data:
            logger.warning("No data to save")
            return

        try:
            # Save to master file first
            self.save_master_data(data)

            # Create location and date-specific directory
            current_date = datetime.now().strftime('%Y%m%d')
            location_dir = os.path.join(output_dir, location)
            date_dir = os.path.join(location_dir, current_date)
            os.makedirs(date_dir, exist_ok=True)

            # Get existing data from today's files
            existing_data = []
            json_files = [f for f in os.listdir(date_dir) if f.endswith('.json')]
            for json_file in json_files:
                try:
                    with open(os.path.join(date_dir, json_file), 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        if isinstance(file_data, list):
                            existing_data.extend(file_data)
                except Exception as e:
                    logger.error(f"Error reading file {json_file}: {str(e)}")

            # Merge new data with existing data
            all_data = existing_data + data
            
            # Remove duplicates based on URL
            seen_urls = set()
            unique_data = []
            for item in all_data:
                if item['url'] not in seen_urls:
                    seen_urls.add(item['url'])
                    unique_data.append(item)

            # Create new filename with timestamp
            timestamp = datetime.now().strftime('%H%M')
            filename = os.path.join(date_dir, f'restaurants_{timestamp}.json')

            # Save merged data
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(unique_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(unique_data)} restaurants to {filename}")
            self.last_save_time = time.time()

            # Save visited URLs
            self.save_visited_urls()

            # KEEP OLD FILES - DON'T REMOVE THEM
            # Instead, keep track of how many files we have
            if len(json_files) > 10:  # If we have more than 10 files, log a warning
                logger.warning(f"Directory {date_dir} has {len(json_files)} JSON files. Consider manual cleanup.")

            # Cleanup old date directories (keep last 7 days)
            self._cleanup_old_dates(location_dir)

        except Exception as e:
            logger.error(f"Error saving data: {str(e)}")
            # Create error backup with timestamp
            error_file = os.path.join(output_dir, f"error_backup_{int(time.time())}.json")
            try:
                with open(error_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                logger.info(f"Created error backup at {error_file}")
            except Exception as backup_error:
                logger.error(f"Failed to create error backup: {str(backup_error)}")

    def _cleanup_old_dates(self, location_dir):
        """Cleanup old date directories, keeping only the last 7 days"""
        try:
            # Get all date directories
            date_dirs = [d for d in os.listdir(location_dir) 
                        if os.path.isdir(os.path.join(location_dir, d)) 
                        and d.isdigit() and len(d) == 8]
            
            # Sort by date (newest first)
            date_dirs.sort(reverse=True)
            
            # Remove directories older than 7 days
            for old_dir in date_dirs[7:]:
                old_path = os.path.join(location_dir, old_dir)
                try:
                    import shutil
                    shutil.rmtree(old_path)
                    logger.info(f"Removed old date directory: {old_dir}")
                except Exception as e:
                    logger.error(f"Error removing directory {old_dir}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error during date directory cleanup: {str(e)}")

    def get_soup(self, url, retries=3):
        """Get BeautifulSoup object from URL with retries"""
        for attempt in range(retries):
            try:
                logger.info(f"Fetching URL: {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                if "captcha" in response.text.lower() or "please enable js" in response.text.lower():
                    logger.warning("Captcha detected! Try using a different approach or wait longer between requests")
                    if attempt < retries - 1:
                        wait_time = (attempt + 1) * 60
                        logger.info(f"Retrying after {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                return soup
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching URL {url}: {e}")
                if attempt < retries - 1:
                    wait_time = (attempt + 1) * 30
                    logger.info(f"Retrying after {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to fetch {url} after {retries} attempts")
        return None

    def _valid_name(self, txt: str) -> bool:
        """Filter out invalid restaurant names"""
        if not txt or len(txt) < 3:
            return False
        bad = ["see tickets", "reviews", "review of", "tickets", "see menu"]
        if any(k in txt.lower() for k in bad):
            return False
        if re.fullmatch(r"[\d\W_]+", txt):
            return False
        return True

    def get_restaurant_listings(self, url=None, page=1):
        """Get restaurant listings from a page"""
        current_url = url or self.base_url
        original_url = current_url

        if page > 1:
            if "oa" in current_url:
                current_url = re.sub(r'oa\d+', f'oa{(page-1)*30}', current_url)
            else:
                # For restaurant pages, adjust URL pagination format if needed
                if "FindRestaurants" in current_url:
                    # For FindRestaurants, we need to add the 'o=' parameter for pagination
                    # This appears to be the correct offset parameter for TripAdvisor restaurants
                    if "o=" in current_url:
                        current_url = re.sub(r'o=\d+', f'o={(page-1)*30}', current_url)
                    else:
                        current_url = f"{current_url}&o={(page-1)*30}"
                        
                    # Add additional pagination parameters if missing
                    if "itags=" not in current_url:
                        current_url += "&itags=10591"
                    if "sortOrder=" not in current_url:
                        current_url += "&sortOrder=relevance"
                else:
                    current_url = current_url.replace('.html', f'-oa{(page-1)*30}.html')
        
        # Print detailed debug information about pagination
        logger.info(f"Original URL: {original_url}")
        logger.info(f"Paginated URL for page {page}: {current_url}")

        soup = self.get_soup(current_url)
        if not soup:
            return [], False

        restaurants = []
        local_seen = set()  # Track inside this call only
        url_counter = {}    # Count duplicate URLs in this page

        selectors = [
            'a[data-automation="restaurantTitleLink"]',  # Primary restaurant link selector
            'a[data-automation="poiTitleLink"]',
            'div[data-automation="restaurant"] a[href^="/Restaurant_Review"]',
            'a[href^="/Restaurant_Review"]'
        ]

        # First count all URLs to detect duplicates within the same page
        all_links = []
        for sel in selectors:
            all_links.extend(soup.select(sel))
            
        for a in all_links:
            href = a.get('href')
            if not href:
                continue
            if not href.startswith('http'):
                href = urljoin("https://www.tripadvisor.com", href)
            url_counter[href] = url_counter.get(href, 0) + 1
        
        # Now extract valid restaurants and log duplicates
        for sel in selectors:
            for a in soup.select(sel):
                href = a.get('href')
                name = a.get_text(strip=True)
                if not href or not self._valid_name(name):
                    continue
                if not href.startswith('http'):
                    href = urljoin("https://www.tripadvisor.com", href)
                if href in local_seen:
                    continue
                    
                local_seen.add(href)
                restaurants.append({"name": name, "url": href})

        # Log information about duplicates
        duplicate_urls = [url for url, count in url_counter.items() if count > 1]
        if duplicate_urls:
            logger.info(f"Found {len(duplicate_urls)} URLs that appear multiple times on this page")
            if len(duplicate_urls) < 5:
                for url in duplicate_urls:
                    logger.info(f"  Duplicate URL: {url} (appears {url_counter[url]} times)")
            else:
                logger.info(f"  First duplicate: {duplicate_urls[0]} (appears {url_counter[duplicate_urls[0]]} times)")
        
        # Print the number of unique restaurants found
        logger.info(f"Found {len(restaurants)} unique restaurants on page {page} (from {len(all_links)} total links)")
        
        # Count visited restaurants in the current batch
        already_visited = [item for item in restaurants if item["url"] in self.visited_urls]
        if already_visited:
            logger.info(f"{len(already_visited)} of these restaurants have been visited before")
        
        # Check for next page button and print debug info
        next_page_link = soup.select_one('a[href*="o="][aria-label*="Next"]') or soup.select_one('a[href*="oa"][aria-label*="Next"]')
        has_next_page = bool(next_page_link)
        
        if has_next_page and next_page_link:
            next_href = next_page_link.get('href', '')
            if not next_href.startswith('http'):
                next_href = urljoin("https://www.tripadvisor.com", next_href)
            logger.info(f"Next page link found: {next_href}")
        else:
            # Look for pagination indicators even if Next button is not found
            pagination_elems = soup.select('a.pageNum')
            if pagination_elems:
                logger.info(f"Found pagination elements: {len(pagination_elems)} page numbers")
                last_page = max([int(a.get_text(strip=True)) for a in pagination_elems if a.get_text(strip=True).isdigit()], default=0)
                logger.info(f"Last page number: {last_page}")
                has_next_page = page < last_page
            else:
                logger.info("No pagination elements found")
            
            if not has_next_page:
                logger.info("No next page link found - reached the end of pagination")
        
        return restaurants, has_next_page

    def _extract_clean_address(self, soup):
        """Extract address from the soup"""
        address = None
        
        address_selectors = [
            'span.DsyBj[data-test-target="detailsAddressInfo"]',
            'div[data-automation="location__address"]',
            'a.AYHFM',  # Restaurant address selector
            'a[href^="#MAPVIEW"]',
            'div.czkFU a',
            'button.KTXIj',
            'div.XQaIe',
            'div.euDRl > a',
            'div[data-automation="WebPresentation_LocalizationMapCard"] div.euDRl',
            'div[data-automation="WebPresentation_PoiLocationCard"] div.euDRl',
            'span[data-automation="restaurantsMapLinkOnName"]'
        ]
        
        for selector in address_selectors:
            addr_elem = soup.select_one(selector)
            if addr_elem:
                address_text = addr_elem.get_text(strip=True)
                address_text = re.sub(r'^Address\s*', '', address_text)
                if address_text and len(address_text) > 5 and len(address_text) < 200:
                    address = address_text
                    break
        
        # Try additional methods if not found
        if not address:
            addr_pattern = re.compile(r'(\d+\s+[\w\s]+,\s+[\w\s]+,\s+[A-Za-z\s]+\s+\d+\s+[A-Za-z]+)', re.IGNORECASE)
            for script in soup.find_all('script'):
                if script.string and addr_pattern.search(script.string):
                    address = addr_pattern.search(script.string).group(1)
                    break
            
            if not address:
                for div in soup.find_all('div'):
                    text = div.get_text(strip=True)
                    if addr_pattern.search(text):
                        address = addr_pattern.search(text).group(1)
                        break
                        
        return address
    
    def _extract_opening_hours(self, soup):
        """Extract restaurant opening hours"""
        hours = None
        
        hours_selectors = [
            'div[data-automation="WebPresentation_PoiOpenHours"]',
            'div.IMlHP',
            'div.QvzAT',
            'div.YbkpN',
            'div.JguWG:contains("Open now")',
            'div:contains("Open today")',
            'div:contains("Hours:")',
            'div[data-section-id="HoursSection"]'
        ]
        
        for selector in hours_selectors:
            if ':contains' in selector:
                base_selector, contains_text = selector.split(':contains(')
                contains_text = contains_text.rstrip(')')
                contains_text = contains_text.strip('"\'')
                
                elements = soup.select(base_selector)
                for elem in elements:
                    if contains_text in elem.get_text():
                        hours_text = elem.get_text(strip=True)
                        hours_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M\s*-\s*\d{1,2}:\d{2}\s*[AP]M)', hours_text)
                        if hours_match:
                            hours = hours_match.group(1)
                        else:
                            hours = hours_text
                        break
            else:
                hours_elem = soup.select_one(selector)
                if hours_elem:
                    hours_text = hours_elem.get_text(strip=True)
                    if hours_text and ('open' in hours_text.lower() or 'hour' in hours_text.lower() or 'am' in hours_text.lower() or 'pm' in hours_text.lower()):
                        hours_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M\s*-\s*\d{1,2}:\d{2}\s*[AP]M)', hours_text)
                        if hours_match:
                            hours = hours_match.group(1)
                        else:
                            if len(hours_text) < 50:
                                hours = hours_text
                        break
        
        # Try looking for time pattern directly
        if not hours:
            time_pattern = re.compile(r'\d{1,2}:\d{2}\s*[AP]M\s*-\s*\d{1,2}:\d{2}\s*[AP]M')
            time_elems = soup.find_all(string=time_pattern)
            if time_elems:
                for elem in time_elems:
                    match = time_pattern.search(elem)
                    if match:
                        hours = match.group(0)
                        break
        
        return hours

    def _extract_price_range(self, soup):
        """Extract restaurant price range"""
        price_range = None
        
        price_selectors = [
            'div.WlYyy.cPsXC div',  # Price level selector
            'span.DsyBj i.czLpV',   # Price level icons
            'div.gZwVG span[data-automation="priceLevelLink"]',
            'div.eCPON span',
            'div[data-section-id="restaurant_detail"]'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                text = price_elem.get_text(strip=True)
                # Look for $ symbols
                if re.search(r'[$€£¥]', text):
                    price_range = text
                    break
                # Look for price range text
                price_match = re.search(r'(inexpensive|moderate|expensive|very expensive|budget|mid-range|fine dining)', text, re.IGNORECASE)
                if price_match:
                    price_range = price_match.group(0)
                    break
                    
        # Check for price level indicators ($$-$$$)
        if not price_range:
            for script in soup.find_all('script', {'type': 'application/ld+json'}):
                if script.string:
                    try:
                        data = json.loads(script.string)
                        if 'priceRange' in data:
                            price_range = data['priceRange']
                            break
                    except:
                        pass
                        
        return price_range

    def _extract_cuisine_types(self, soup):
        """Extract restaurant cuisine types"""
        cuisines = []
        
        cuisine_selectors = [
            'div.gZwVG a[href*="Cuisine"]',
            'a[href*="c="][data-automation="cuisineLink"]',
            'div.eCPON a[href*="c="]',
            'div[data-automation="restaurantDetailsCuisinesFeatures"] a',
            'a[href*="-c"]',  # Additional cuisine link format
            'span.SrqKb',     # Cuisine labels
            'div.OTyAN:contains("CUISINES")',  # Cuisine section
            'div.UrHfF span'  # Additional cuisine span elements
        ]
        
        for selector in cuisine_selectors:
            if ':contains' in selector:
                base_selector, contains_text = selector.split(':contains(')
                contains_text = contains_text.rstrip(')')
                contains_text = contains_text.strip('"\'')
                
                elements = soup.select(base_selector)
                for elem in elements:
                    if contains_text in elem.get_text():
                        # Try to find cuisine info in the next sibling element
                        next_elem = elem.find_next_sibling()
                        if next_elem:
                            cuisine_text = next_elem.get_text(strip=True)
                            if cuisine_text and len(cuisine_text) > 2:
                                # Split by commas if multiple cuisines are listed
                                for c in cuisine_text.split(','):
                                    c = c.strip()
                                    if c and c.lower() not in ('restaurant', 'restaurants'):
                                        cuisines.append(c)
            else:
                cuisine_elems = soup.select(selector)
                for elem in cuisine_elems:
                    cuisine = elem.get_text(strip=True)
                    if cuisine and cuisine.lower() not in ('restaurant', 'restaurants'):
                        cuisines.append(cuisine)
        
        # Try to extract cuisines from meta tags
        for meta in soup.find_all('meta', {'property': 'og:description'}):
            if meta.has_attr('content'):
                content = meta['content'].lower()
                common_cuisines = [
                    'vietnamese', 'italian', 'french', 'japanese', 'chinese', 
                    'thai', 'indian', 'korean', 'mexican', 'american', 'seafood',
                    'vegetarian', 'vegan', 'asian', 'fusion', 'mediterranean'
                ]
                for cuisine in common_cuisines:
                    if cuisine in content and cuisine not in [c.lower() for c in cuisines]:
                        cuisines.append(cuisine.title())
                        
        # Try to extract cuisines from schema.org JSON data
        for script in soup.find_all('script', {'type': 'application/ld+json'}):
            if script.string:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and 'servesCuisine' in data:
                        if isinstance(data['servesCuisine'], list):
                            for cuisine in data['servesCuisine']:
                                if cuisine and cuisine.lower() not in [c.lower() for c in cuisines]:
                                    cuisines.append(cuisine)
                        elif isinstance(data['servesCuisine'], str):
                            cuisine = data['servesCuisine']
                            if cuisine and cuisine.lower() not in [c.lower() for c in cuisines]:
                                cuisines.append(cuisine)
                except:
                    pass
        
        # Filter out navigation elements and irrelevant items
        filtered_cuisines = []
        irrelevant_keywords = [
            'tour', 'hotel', 'hostel', 'bed and breakfast', 'contact', 
            'campground', 'restaurant in', 'more on', 'read more', 
            'view more', 'for families', 'with outdoor', 'with delivery',
            'for special', 'family', 'ho chi minh city', 'restaurant for'
        ]
        
        valid_cuisines = [
            'vietnamese', 'italian', 'french', 'japanese', 'chinese', 'thai', 'indian', 
            'korean', 'mexican', 'american', 'seafood', 'vegetarian', 'vegan', 'asian', 
            'fusion', 'mediterranean', 'european', 'cafe', 'coffee', 'tea', 'bakery', 
            'pastry', 'dessert', 'bar', 'pub', 'wine', 'beer', 'cocktail', 'bbq', 
            'grill', 'steakhouse', 'burger', 'pizza', 'sushi', 'noodle', 'soup', 
            'fast food', 'street food', 'tapas', 'spanish', 'german', 'greek', 
            'middle eastern', 'lebanese', 'turkish', 'african', 'caribbean', 
            'latin american', 'brazilian', 'peruvian', 'healthy', 'organic', 'gluten-free',
            'western', 'eastern', 'contemporary', 'local', 'international', 'regional'
        ]
        
        for cuisine in cuisines:
            c_lower = cuisine.lower()
            # Skip items containing irrelevant keywords
            if any(kw in c_lower for kw in irrelevant_keywords):
                continue
                
            # Include items that are valid cuisines
            if any(vc in c_lower for vc in valid_cuisines):
                filtered_cuisines.append(cuisine)
                continue
                
            # Include items that are short (likely cuisine names)
            if len(cuisine.split()) <= 3 and len(cuisine) < 30:
                filtered_cuisines.append(cuisine)
                
        # Remove duplicates
        return list(dict.fromkeys(filtered_cuisines))

    def _extract_menu_link(self, soup):
        """Extract link to the restaurant menu"""
        menu_link = None
        
        menu_selectors = [
            'a[data-automation="menu"]', 
            'a.hxBaU',
            'a[href*="Menu"]',
            'div.euDRl a[href*="Menu"]',
            'a:contains("See menu")'
        ]
        
        for selector in menu_selectors:
            if ':contains' in selector:
                base_selector, contains_text = selector.split(':contains(')
                contains_text = contains_text.rstrip(')')
                contains_text = contains_text.strip('"\'')
                
                elements = soup.select(base_selector)
                for elem in elements:
                    if contains_text in elem.get_text():
                        if elem.has_attr('href'):
                            href = elem['href']
                            if not href.startswith('http'):
                                href = urljoin("https://www.tripadvisor.com", href)
                            menu_link = href
                            break
            else:
                menu_elem = soup.select_one(selector)
                if menu_elem and menu_elem.has_attr('href'):
                    href = menu_elem['href']
                    if not href.startswith('http'):
                        href = urljoin("https://www.tripadvisor.com", href)
                    menu_link = href
                    break
                    
        return menu_link

    def _clean_name(self, name):
        """Clean up the restaurant name"""
        if not name:
            return "Unknown Restaurant"
            
        name = re.sub(r'If you own this business.*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\d+(\.\d+)?\s+of\s+5\s+bubbles', '', name)
        name = re.sub(r'[\d,]+\s+reviews?', '', name)
        name = re.sub(r'\s*\(\d+\)\s*$', '', name)
        return name.strip()

    def get_restaurant_details(self, restaurant_url):
        """Get detailed information about a restaurant"""
        self._random_delay()
        
        soup = self.get_soup(restaurant_url)
        if not soup:
            return {"url": restaurant_url, "error": "Failed to fetch restaurant page"}
            
        details = {
            "url": restaurant_url
        }
        
        # 1. Extract name
        name_selectors = [
            'div.MhXlV h1',
            'h1.QdLfr',
            'h1.eIegw',
            'h1.HjBfq',
            'div.pZUbB h1',
            'h1',
            'div[data-automation="WebPresentation_RestaurantTitle"] h1'
        ]
        for selector in name_selectors:
            name_elem = soup.select_one(selector)
            if name_elem:
                details["name"] = self._clean_name(name_elem.get_text(strip=True))
                break
        
        # Extract name from URL if not found
        if 'name' not in details or not details['name'] or details['name'] == "Unknown Restaurant":
            try:
                if 'Restaurant_Review' in restaurant_url:
                    url_parts = restaurant_url.split('-')
                    name_part = url_parts[-2] if len(url_parts) > 2 else ""
                    details["name"] = name_part.replace('_', ' ').title()
            except Exception as e:
                logger.error(f"Error extracting name from URL {restaurant_url}: {e}")
                details["name"] = "Unknown Restaurant"
        
        # 2. Extract address
        address = self._extract_clean_address(soup)
        if address:
            details["address"] = address
        
        # 3. Extract description/about
        description_selectors = [
            'div.pZUbB div.duhwe span.JguWG',
            'div.DpZHu div',
            'div.LBVLY div.WlYyy',
            'div[data-automation="WebPresentation_RestaurantOverviewSection"]',
            'div.fIrGe',
            'div.euDRl',
            'section[data-automation="WebPresentation_POIAboutSection"] div',
            'div[data-automation="WebPresentation_POIAboutSection"] div'
        ]
        for selector in description_selectors:
            desc_elems = soup.select(selector)
            if desc_elems:
                for desc_elem in desc_elems:
                    description_text = desc_elem.get_text(strip=True)
                    if description_text and len(description_text) > 20:
                        details["description"] = description_text
                        break
                if "description" in details:
                    break
        
        # 4. Extract opening hours
        opening_hours = self._extract_opening_hours(soup)
        if opening_hours:
            details["opening_hours"] = opening_hours
        
        # 5. Extract cuisine types
        cuisines = self._extract_cuisine_types(soup)
        if cuisines:
            details["cuisines"] = cuisines
        
        # 6. Extract price range
        price_range = self._extract_price_range(soup)
        if price_range:
            details["price_range"] = price_range
        
        # 7. Extract menu link
        menu_link = self._extract_menu_link(soup)
        if menu_link:
            details["menu_url"] = menu_link
        
        # 8. Extract rating
        rating_selectors = [
            '[data-automation="bubbleRatingValue"]', 
            'span.UctUV',
            'div.grdwI span.UctUV',
            'span.ui_bubble_rating',
            'div.rWAMq',
            'div.WdWxQ'
        ]
        for selector in rating_selectors:
            rating_elem = soup.select_one(selector)
            if rating_elem:
                text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'(\d+\.?\d*)\s*(?:of\s*\d+)?', text)
                if rating_match:
                    try:
                        rating_val = float(rating_match.group(1))
                        if 0 <= rating_val <= 5:
                            details["rating"] = rating_val
                            break
                    except ValueError:
                        pass
        
        # 9. Extract number of reviews
        reviews_selectors = [
            '[data-automation="bubbleReviewCount"]', 
            'a.iUttq',
            'span.jqKwK',
            'a.UctQk',
            'span.DJzgG',
            'span.JguWG'
        ]
        for selector in reviews_selectors:
            reviews_elem = soup.select_one(selector)
            if reviews_elem:
                text = reviews_elem.get_text(strip=True)
                reviews_match = re.search(r'([\d,]+)\s*reviews?', text)
                if reviews_match:
                    details["num_reviews"] = reviews_match.group(1)
                    break

        # Extract summary reviews
        reviews_selectors = [
            'div.aaQZA div.biGQs._P.pZUbB.KxBGd',  # Main summary selector
            'div.IGaaH._u._c div.biGQs._P.pZUbB.KxBGd',  # Full path with container
            'div#GAI_REVIEWS div.aaQZA div.biGQs._P.pZUbB.KxBGd',  # With reviews container ID
            'div.PcCsz.o div.aaQZA div.biGQs._P.pZUbB.KxBGd'  # Complete path
        ]
        for selector in reviews_selectors:
            reviews_elem = soup.select_one(selector)
            if reviews_elem:
                text = reviews_elem.get_text(strip=True)
                if text and len(text) > 50 and "reviews" in text.lower():  # Ensure it's a substantial review summary
                    details["review_summary"] = text
                    break

        # 10. Extract restaurant features/amenities
        feature_selectors = [
            'div[data-automation="restaurantDetailsCuisinesFeatures"] div.euDRl',
            'div.eCPON div.euDRl',
            'div[data-automation="WebPresentation_DetailsTags"] div.euDRl'
        ]
        
        features = []
        for selector in feature_selectors:
            feature_elems = soup.select(selector)
            for elem in feature_elems:
                feature_text = elem.get_text(strip=True)
                # Skip if it's a cuisine (already captured)
                if features or not any(c.lower() in feature_text.lower() for c in cuisines):
                    features.append(feature_text)
        
        if features:
            details["features"] = list(dict.fromkeys(features))[:5]  # Keep unique, limit to 5
            
        # Add phone numbers
        phones = []
        try:
            # First try to find phone numbers in contact information section
            contact_selectors = [
                'div[data-automation="restaurantContactCard"]',
                'div.euDRl:contains("Phone")',
                'div.czkFU:contains("Phone")',
                'div.YnKZo:contains("Phone")'
            ]
            
            for selector in contact_selectors:
                if ':contains' in selector:
                    base_selector = selector.split(':contains(')[0]
                    elements = soup.select(base_selector)
                    for elem in elements:
                        if 'Phone' in elem.get_text():
                            # Try to find phone number in text
                            phone_text = elem.get_text(strip=True)
                            phone_match = re.search(r'[\+\d][\d\s\-\(\)\.]{8,}', phone_text)
                            if phone_match:
                                phones.append(phone_match.group(0).strip())
                                break
                else:
                    contact_elem = soup.select_one(selector)
                    if contact_elem:
                        # Look for phone links or spans
                        phone_elements = contact_elem.select('a[href^="tel:"], span.biGQs._P.XWJSj.Wb')
                        for phone_elem in phone_elements:
                            if phone_elem.name == 'a' and phone_elem.has_attr('href'):
                                phone = phone_elem['href'].replace('tel:', '')
                                if phone and re.search(r'\d', phone):
                                    phones.append(phone)
                                    break
                            else:
                                phone = phone_elem.get_text(strip=True)
                                if phone and re.search(r'\d', phone):
                                    phones.append(phone)
                                    break
            
            # If no phone found, try direct phone link
            if not phones:
                phone_links = soup.select('a[href^="tel:"]')
                for link in phone_links:
                    phone = link['href'].replace('tel:', '')
                    if phone and re.search(r'\d', phone):
                        phones.append(phone)
                        break
            
            # Try to find phone numbers in any text that matches phone format
            if not phones:
                phone_pattern = re.compile(r'[\+\d][\d\s\-\(\)\.]{8,}')
                for text in soup.stripped_strings:
                    if 'phone' in text.lower() or 'tel' in text.lower():
                        phone_match = phone_pattern.search(text)
                        if phone_match:
                            phones.append(phone_match.group(0).strip())
                            break
                            
        except Exception as e:
            logger.error(f"Error extracting phone numbers: {str(e)}")
                        
        if phones:
            # Clean up the phone number
            phone = phones[0]
            phone = re.sub(r'\s+', ' ', phone)  # Normalize whitespace
            phone = phone.strip()
            details["phone"] = phone

        # Extract example reviews
        example_reviews = []
        try:
            # First try to find review containers
            review_containers = soup.select('div[data-test-target="review-body"]')
            
            if review_containers:
                for container in review_containers[:3]:  # Get up to 3 reviews
                    review_text = None
                    # Try different selectors for review text based on new structure
                    text_selectors = [
                        'span.JguWG',  # New main review text selector
                        'div.biGQs._P.pZUbB.KxBGd',  # Alternative review text container
                        'div.f1rGe._T.bgMZj span.JguWG',  # Full path to review text
                        'div._T.FKffI div.f1rGe._T.bgMZj span.JguWG',  # Complete path
                    ]
                    
                    for selector in text_selectors:
                        review_elem = container.select_one(selector)
                        if review_elem:
                            review_text = review_elem.get_text(strip=True)
                            if review_text:
                                break
                    
                    if review_text and len(review_text) > 10:  # Ensure it's a substantial review
                        example_reviews.append(review_text)
            
            # If no reviews found in containers, try direct selectors
            if not example_reviews:
                review_selectors = [
                    'span.JguWG',  # Direct review text selector
                    'div.biGQs._P.pZUbB.KxBGd span.JguWG',  # Alternative path
                    'div[data-test-target="review-body"] span.JguWG',  # Full container path
                    'div.f1rGe._T.bgMZj span.JguWG'  # Another alternative path
                ]
                
                for selector in review_selectors:
                    review_elements = soup.select(selector)
                    for elem in review_elements[:5]:  # Get up to 3 reviews
                        review_text = elem.get_text(strip=True)
                        if review_text and len(review_text) > 10:
                            example_reviews.append(review_text)
                            if len(example_reviews) >= 3:
                                break
                    if len(example_reviews) >= 3:
                        break
            
            # Clean up reviews
            example_reviews = [
                re.sub(r'\s+', ' ', review).strip()
                for review in example_reviews
                if review and len(review.strip()) > 10
            ]
            
            # Remove duplicates while preserving order
            example_reviews = list(dict.fromkeys(example_reviews))
            
        except Exception as e:
            logger.error(f"Error extracting reviews: {str(e)}")
        
        if example_reviews:
            details["example_reviews"] = example_reviews[:3]  # Ensure we only keep up to 3 reviews

        # Extract media (images/videos) from reviews
        try:
            media_selectors = [
                'div[data-section-signature="photo_viewer"] picture.NhWcC._R.mdkdE.afQPz.eXZKw source[srcset]',  # Image sources
                'div[data-testid="carousel-with-strip"] picture source[srcset]',  # Carousel images
                'div.SQIuW.wSSLS picture source[srcset]',  # Review images
                'div.XKYCB.wSSLS picture source[srcset]',  # Alternative image structure
                'div[data-test-target="review-body"] video source',  # Video sources
                'div.reviewCard video source'  # Alternative video structure
            ]
            
            media_urls = []
            for selector in media_selectors:
                media_elements = soup.select(selector)
                for elem in media_elements:
                    if elem.has_attr('srcset'):
                        try:
                            # Parse srcset to get the highest quality image
                            srcset = elem['srcset']
                            # Split srcset into URL-scale pairs
                            pairs = []
                            for pair in srcset.split(','):
                                parts = pair.strip().split()
                                if len(parts) >= 2:  # Only add if we have both URL and scale
                                    pairs.append((parts[0], parts[1]))
                                elif len(parts) == 1:  # If we only have URL, assume scale 1x
                                    pairs.append((parts[0], '1x'))
                            
                            # Get URL with highest scale (2x if available)
                            highest_quality_url = None
                            for url, scale in pairs:
                                if scale == '2x':
                                    highest_quality_url = url
                                    break
                            if not highest_quality_url and pairs:
                                highest_quality_url = pairs[-1][0]  # Take the last URL if no 2x
                            
                            if highest_quality_url:
                                # Clean up the URL
                                clean_url = highest_quality_url.strip()
                                if clean_url not in media_urls:
                                    media_urls.append(clean_url)
                        except Exception as e:
                            logger.error(f"Error parsing srcset: {str(e)}")
                            # Try to get the first URL if srcset parsing fails
                            try:
                                first_url = elem['srcset'].split(',')[0].strip().split()[0]
                                if first_url and first_url not in media_urls:
                                    media_urls.append(first_url)
                            except:
                                pass
                    elif elem.has_attr('src'):
                        # For video sources or single-URL images
                        src_url = elem['src'].strip()
                        if src_url not in media_urls:
                            media_urls.append(src_url)

            if media_urls:
                details["media_urls"] = media_urls[:10]  # Limit to first 10 media items
                # Set the first media as main_image if no main image exists
                if "main_image" not in details and media_urls:
                    details["main_image"] = media_urls[0]
                    
        except Exception as e:
            logger.error(f"Error extracting media from reviews: {str(e)}")

        # Add to visited urls - only after successfully getting details
        self.visited_urls.add(restaurant_url)
        if details["name"]:
            self.visited_restaurants.add(details["name"].lower())
            
        return details

    def crawl_restaurants(self, max_pages=3, max_restaurants=None, threads=4, start_page=1, output_dir="data_restaurants", location="hcmc", ignore_duplicates=False):
        """Crawl restaurants and extract details"""
        all_listings, page, more = [], start_page, True
        detailed = []
        
        logger.info(f"Starting crawl from page {start_page} with max_pages={max_pages}, max_restaurants={max_restaurants}")
        
        # First, collect all listings
        while more and (page - start_page + 1) <= max_pages:
            logger.info(f"Crawling page {page}")
            lst, more = self.get_restaurant_listings(page=page)
            logger.info(f"Found {len(lst)} restaurants on page {page}")
            
            if not lst:
                logger.warning(f"No restaurants found on page {page}, stopping listing collection")
                break
                
            # Print all URLs before filtering to help with debugging
            if len(lst) < 10:
                logger.info(f"URLs found on page {page}:")
                for idx, item in enumerate(lst):
                    logger.info(f"  {idx+1}. {item['name']} - {item['url']}")
            else:
                logger.info(f"First 5 URLs found on page {page}:")
                for idx, item in enumerate(lst[:5]):
                    logger.info(f"  {idx+1}. {item['name']} - {item['url']}")
                
            # Filter out already visited URLs
            new_listings = [item for item in lst if item["url"] not in self.visited_urls]
            logger.info(f"Found {len(new_listings)} new restaurants after filtering visited URLs")
            
            # Check if we should continue despite duplicates
            if not new_listings and not ignore_duplicates:
                logger.warning("No new restaurant listings found.")
                break
            elif not new_listings and ignore_duplicates:
                logger.info("All restaurants on this page were duplicates, but continuing due to --ignore-duplicates flag")
                page += 1
                self._random_delay()
                continue
            
            all_listings.extend(new_listings)
            if max_restaurants and len(all_listings) >= max_restaurants:
                logger.info(f"Reached max_restaurants limit ({max_restaurants})")
                all_listings = all_listings[:max_restaurants]
                break
            
            page += 1
            self._random_delay()

        if not all_listings and not ignore_duplicates:
            logger.warning("No new restaurant listings found.")
            return detailed
        elif not all_listings and ignore_duplicates:
            logger.info("Finished crawling, but all restaurants were duplicates. Returning empty results.")
            return detailed

        logger.info(f"Starting to crawl details for {len(all_listings)} restaurants")
        with ThreadPoolExecutor(max_workers=threads) as executor:
            future_map = {executor.submit(self.get_restaurant_details, it["url"]): it for it in all_listings}
            for fut in as_completed(future_map):
                it = future_map[fut]
                try:
                    det = fut.result()
                    if "error" in det:
                        logger.warning(f"Error getting details for {it['url']}: {det['error']}")
                        continue
                    detailed.append({**it, **det})
                    logger.info(f"✓ {det.get('name')}")
                    
                    # Save periodically
                    if self._should_save():
                        self.save_data(detailed, output_dir, location)
                        
                except Exception as e:
                    logger.error(f"{e} – {it['url']}")

        # Final save
        self.save_data(detailed, output_dir, location)
        logger.info(f"Found {len(detailed)} unique restaurants")
        return detailed


def main():
    parser = argparse.ArgumentParser(description='TripAdvisor Restaurant Crawler')
    parser.add_argument('--url', type=str, 
                      help='URL to crawl', 
                      default="https://www.tripadvisor.com/FindRestaurants?geo=293925&establishmentTypes=10591%2C11776%2C16548%2C16556%2C21908%2C9900%2C9901%2C9909&broadened=false")
    parser.add_argument('--max-pages', type=int, default=3,
                      help='Maximum number of pages to crawl')
    parser.add_argument('--start-page', type=int, default=1,
                      help='Page number to start crawling from')
    parser.add_argument('--max-restaurants', type=int,
                      help='Maximum number of restaurants to crawl')
    parser.add_argument('--delay', type=float, default=4.0,
                      help='Delay between requests in seconds')
    parser.add_argument('--threads', type=int, default=4,
                      help='Number of concurrent threads')
    parser.add_argument('--output-dir', default='data_restaurants',
                      help='Output directory for JSON files')
    parser.add_argument('--location', default='hcmc',
                      help='Location name for organizing files')
    parser.add_argument('--save-interval', type=int, default=15,
                      help='Minutes between periodic saves (default: 15)')
    parser.add_argument('--ignore-duplicates', action='store_true',
                      help='Continue crawling even when all results are duplicates')
    args = parser.parse_args()

    crawler = RestaurantCrawler(
        base_url=args.url,
        delay=args.delay,
        save_interval=args.save_interval
    )
    
    crawler.crawl_restaurants(
        max_pages=args.max_pages,
        start_page=args.start_page,
        max_restaurants=args.max_restaurants,
        threads=args.threads,
        output_dir=args.output_dir,
        location=args.location,
        ignore_duplicates=args.ignore_duplicates
    )

if __name__ == "__main__":
    main()
