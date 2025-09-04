import time
import random
import os
import csv
import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.mouse_button import MouseButton
import logging

# Configure logging
logging.basicConfig(
    filename='zillow_scraper.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Also log to console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

ZIPCODES = [
    '33009', '33019', '33119', '33128', '33129', '33130', '33131', '33139', '33140', '33141', '33149', '33154', '33160',
    '33180', '33239'
]

class ZillowScraper:
    def __init__(self, options=None):
        logging.info("Initializing ZillowScraper...")

        # Create timestamp for the output file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.output_file = 'zillow_results.csv'
        logging.info(f"Output will be saved to: {self.output_file}")

        # Initialize the CSV file with headers
        self.fieldnames = [
            'ZIPCODE', 'MLS', 'PRICE', 'ADDRESS', 'BEDS', 'BATHS', 'SQFT',
            'URL', 'MAPS_URL', 'DAYS_ON_MARKET', 'AGENT_NAME', 'AGENT_PHONE'
        ]

        # Always overwrite and create the CSV file with headers
        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()

        # Initialize Chrome with version matching
        if options is None:
            options = uc.ChromeOptions()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--start-maximized')
            options.add_argument('--allow-downgrade-browser-version')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--enable-javascript')
            options.add_argument('--disable-infobars')
            options.add_argument("--disable-notifications")
            options.add_argument('--version-mismatch-warning=false')
            # Random user agent that matches our Chrome version
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.7258.155 Safari/537.36')

        try:
            self.driver = uc.Chrome(
                options=options,
                version_main=139  # Match the current Chrome version
            )
            logging.info("Successfully initialized Chrome with version 139")
        except Exception as e:
            logging.error(f"Failed to initialize Chrome with version 139: {str(e)}")
            raise  # Re-raise the exception to stop execution

        # Set random window size
        self.driver.set_window_size(1366, 768)

        # Additional CDP commands to make browser more stealthy
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
        })

        # Execute JavaScript to make WebDriver object undefined
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Initialize instance variables
        self.stop_after_first = False  # Default to scraping all listings
        self.current_zipcode = None
        logging.info("ZillowScraper initialized successfully")

    def apply_filters(self):
        """Apply filters for price and beds on the search results page"""
        logging.info("Applying filters to search results")
        wait = WebDriverWait(self.driver, 10)
        
        # Apply price filter (min $200,000)
        try:
            # Click the price filter button
            price_selectors = [
                '//*[@id="price"]/button',
                '//button[contains(@class, "price-button")]',
                '//button[contains(text(), "Price")]',
                '//button[contains(@aria-label, "Price")]'
            ]
                
            price_button = None
            for selector in price_selectors:
                try:
                    price_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    price_button.click()
                    time.sleep(2)
                    logging.info(f"Opened price filter using selector: {selector}")
                    break
                except Exception:
                    continue
                
            if not price_button:
                logging.warning("Could not find price button with any selector")
                return False
                
            # Find and set the min price input
            price_input_selectors = [
                'input[aria-label="Price min"]',
                'input[placeholder*="Min Price"]',
                'input[name="price-min"]'
            ]
            
            min_price_input = None
            for selector in price_input_selectors:
                try:
                    min_price_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    min_price_input.click()
                    time.sleep(1)
                    logging.info(f"Found price input using selector: {selector}")
                    break
                except Exception:
                    continue
                
            if min_price_input:
                # Clear any existing value and send new price
                min_price_input.clear()
                min_price_input.send_keys("200000")
                time.sleep(1)
                logging.info("Set minimum price filter to $200,000")
                
                # Click apply button
                apply_price = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="price"]/div/footer/div/div/button')))
                apply_price.click()
                time.sleep(2)
                logging.info("Applied price filter")
            else:
                logging.warning("Could not find minimum price input with any selector")
                
            # Apply beds filter (2+ beds)
            beds_selectors = [
                '//*[@id="beds"]/button',
                '//button[contains(@class, "beds-button")]',
                '//button[contains(text(), "Beds")]',
                '//button[contains(@aria-label, "Beds")]'
            ]
                
            beds_button = None
            for selector in beds_selectors:
                try:
                    beds_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    beds_button.click()
                    time.sleep(2)
                    logging.info(f"Opened beds filter using selector: {selector}")
                    break
                except Exception:
                    continue
                    
            if beds_button:
                # Click 2+ beds option
                two_plus_beds_selectors = [
                    "//button[contains(text(), '2+')]",
                    "//button[contains(@aria-label, '2 or more beds')]",
                    "//button[contains(@class, 'two-plus-beds')]"
                ]
                
                two_plus_beds = None
                for selector in two_plus_beds_selectors:
                    try:
                        two_plus_beds = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        two_plus_beds.click()
                        time.sleep(1)
                        logging.info(f"Selected 2+ beds using selector: {selector}")
                        break
                    except Exception:
                        continue
                
                if two_plus_beds:
                    # Click apply button
                    apply_beds_selectors = [
                        '//*[@id="beds"]/div/footer/div/div/button',
                        '//button[contains(text(), "Apply")]',
                        '//button[contains(@aria-label, "Apply")]',
                        '//button[contains(@class, "apply-button")]'
                    ]
                    
                    for selector in apply_beds_selectors:
                        try:
                            apply_beds = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                            apply_beds.click()
                            time.sleep(2)
                            logging.info(f"Applied beds filter using selector: {selector}")
                            break
                        except Exception:
                            continue
                    
                    logging.info("Successfully applied 2+ beds filter")
                else:
                    logging.warning("Could not find 2+ beds option")
            else:
                logging.warning("Could not find beds button with any selector")
            
            # Wait for filters to be applied and results to load
            time.sleep(3)
            return True
            
        except Exception as e:
            logging.error(f"Error applying filters: {str(e)}")
            return False
            
    def sort_by_price_low_to_high(self):
        """Sort listings by price (low to high)"""
        logging.info("Attempting to sort listings by price (low to high)")
        wait = WebDriverWait(self.driver, 10)
        
        try:
            # Click the sort dropdown
            sort_button_selectors = [
                '//button[contains(@aria-label, "Sort")]',
                '//button[contains(text(), "Sort")]',
                '//*[@id="sort-dropdown"]/button',
                '//button[contains(@class, "sort-button")]',
                '//button[contains(@data-testid, "sort-button")]'
            ]
            
            sort_button = None
            for selector in sort_button_selectors:
                try:
                    sort_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    sort_button.click()
                    time.sleep(2)
                    logging.info(f"Clicked sort dropdown using selector: {selector}")
                    break
                except Exception:
                    continue
                    
            if not sort_button:
                logging.warning("Could not find sort dropdown button with any selector")
                return False
                
            # Click the "Price (low to high)" option
            sort_option_selectors = [
                '//button[contains(text(), "Price (low to high)")]',
                '//button[contains(@aria-label, "Price (low to high)")]',
                '//li[contains(text(), "Price (low to high)")]',
                '//div[contains(text(), "Price (low to high)")]',
                '//span[contains(text(), "Price (low to high)")]'
            ]
            
            sort_option = None
            for selector in sort_option_selectors:
                try:
                    sort_option = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    sort_option.click()
                    time.sleep(3)  # Wait for sorting to take effect
                    logging.info(f"Selected 'Price (low to high)' option using selector: {selector}")
                    return True
                except Exception:
                    continue
                    
            if not sort_option:
                logging.warning("Could not find 'Price (low to high)' option with any selector")
                return False
                
        except Exception as e:
            logging.error(f"Error sorting listings by price: {str(e)}")
            return False

    def search_zipcode(self, zipcode):
        """Search for listings in a specific zipcode"""
        self.current_zipcode = zipcode
        
        # Construct URL with zipcode
        url = f"https://www.zillow.com/homes/{zipcode}_rb/"
        logging.info(f"Using search URL: {url}")
        
        # Delete all cookies before each search
        self.driver.delete_all_cookies()
        
        # Add random delay between searches
        time.sleep(2 + random.random() * 3)
        
        logging.info(f"Attempting to load URL: {url}")
        try:
            self.driver.get(url)
            logging.info(f"Successfully loaded URL: {url}")
        except Exception as e:
            logging.error(f"Error loading URL {url}: {str(e)}")
            return
            
        time.sleep(5)  # Increased initial wait time
        
        # Apply filters
        logging.info("Applying filters to search results")
        self.apply_filters()
        
        # Sort listings by price (low to high)
        logging.info("Sorting listings by price (low to high)")
        self.sort_by_price_low_to_high()
        
        # Process listings
        self.process_listings(zipcode)

    def process_listings(self, zipcode, max_listings=5):
        """Process multiple listings on the search results page"""
        try:
            # Wait for the search results grid to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="grid-search-results"]'))
            )
            
            # Get all listing URLs
            grid = self.driver.find_element(By.XPATH, '//*[@id="grid-search-results"]')
            listings = grid.find_elements(By.CSS_SELECTOR, 'ul > li')
            
            if not listings:
                logging.warning("No listings found on the search results page")
                return
                
            logging.info(f"Found {len(listings)} listings on the search results page")
            
            # Collect listing URLs
            listing_urls = []
            link_selectors = [
                'a[data-test="property-card-link"]',
                'a[tabindex="0"]',
                'a.property-card-link',
                'a[href*="/homedetails/"]'
            ]
            
            for listing in listings[:max_listings]:  # Process at most max_listings
                link = None
                for link_selector in link_selectors:
                    try:
                        links = listing.find_elements(By.CSS_SELECTOR, link_selector)
                        if links:
                            link = links[0]
                            break
                    except Exception:
                        pass
                
                if link:
                    url = link.get_attribute('href')
                    if url and url not in listing_urls:
                        listing_urls.append(url)
            
            # Process each listing URL
            for i, url in enumerate(listing_urls, 1):
                logging.info(f"Processing listing {i}/{len(listing_urls)}: {url}")
                
                # Open the listing
                self.driver.get(url)
                time.sleep(3)
                
                # Extract data from the listing
                listing_data = self.extract_listing_data()
                if listing_data:
                    self.save_listing_to_csv(listing_data, zipcode)
                    logging.info(f"Successfully extracted and saved data for listing {i}")
                else:
                    logging.warning(f"Failed to extract data for listing {i}")
                
                # Go back to search results if not the last listing
                if i < len(listing_urls):
                    time.sleep(1)
                    
            logging.info(f"Completed processing {len(listing_urls)} listings")
            
        except Exception as e:
            logging.error(f"Error processing listings: {str(e)}")

    def extract_listing_data(self):
        """Extract data from a listing page"""
        logging.info("Extracting data from listing page")
        try:
            # Wait for price element to confirm page is loaded
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="price"]'))
            )
            
            # Initialize listing data dictionary
            listing_data = {
                'mls': '',
                'price': '',
                'address': '',
                'beds': '',
                'baths': '',
                'sqft': '',
                'url': self.driver.current_url,
                'maps_url': '',
                'days_on_market': '',
                'agent_name': '',
                'agent_phone': ''
            }
            
            # Extract MLS number
            try:
                mls_selectors = [
                    '[data-testid="mls-container"]',
                    '.ds-home-details-chip span',
                    '.ds-listing-agent-info-container span:contains("MLS")',
                    '.data-list-txt span:contains("MLS")',
                ]
                
                for selector in mls_selectors:
                    mls_elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if mls_elems and "MLS" in mls_elems[0].text:
                        listing_data['mls'] = mls_elems[0].text.replace('MLS#', '').replace(':', '').strip()
                        if listing_data['mls']:
                            logging.info(f"✓ Successfully found MLS#: {listing_data['mls']}")
                            break
            except Exception as e:
                logging.warning(f"✗ Failed to extract MLS#: {str(e)}")
            
            # Extract price
            try:
                price_selectors = [
                    '[data-testid="price"] span',
                    '.price-text',
                    '[data-testid="home-info"] .price-text',
                    '.ds-summary-row [data-testid="price"]'
                ]
                
                for selector in price_selectors:
                    price_elem = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if price_elem:
                        listing_data['price'] = price_elem[0].text.strip()
                        logging.info(f"✓ Successfully found price: {listing_data['price']}")
                        break
            except Exception as e:
                logging.warning(f"✗ Failed to extract price: {str(e)}")
            
            # Extract address
            try:
                address_selectors = [
                    '[data-testid="home-details-summary"] h1',
                    '.ds-address-container h1',
                    '[data-testid="address"]',
                    '.summary-container h1'
                ]
                
                for selector in address_selectors:
                    address_elem = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if address_elem:
                        listing_data['address'] = address_elem[0].text.strip()
                        logging.info(f"✓ Successfully found address: {listing_data['address']}")
                        break
            except Exception as e:
                logging.warning(f"✗ Failed to extract address: {str(e)}")
            
            # Extract beds, baths, sqft
            try:
                summary_selectors = [
                    '[data-testid="bed-bath-sqft-fact-container"] span',
                    '.ds-bed-bath-living-area-container span',
                    '.summary-container [data-testid="bed-bath-sqft"]'
                ]
                
                for selector in summary_selectors:
                    summary_elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(summary_elems) >= 3:
                        listing_data['beds'] = summary_elems[0].text.strip().split(' ')[0]
                        listing_data['baths'] = summary_elems[1].text.strip().split(' ')[0]
                        listing_data['sqft'] = summary_elems[2].text.strip().split(' ')[0].replace(',', '')
                        logging.info(f"✓ Successfully found beds: {listing_data['beds']}, baths: {listing_data['baths']}, sqft: {listing_data['sqft']}")
                        break
            except Exception as e:
                logging.warning(f"✗ Failed to extract beds/baths/sqft: {str(e)}")
            
            # Generate Google Maps URL for the address
            if listing_data['address']:
                maps_url = f"https://www.google.com/maps/place/{listing_data['address'].replace(' ', '+')}"
                listing_data['maps_url'] = maps_url
                logging.info(f"✓ Generated Maps URL: {maps_url}")
            
            # Extract days on market
            try:
                dom_selectors = [
                    '[data-testid="days-on-zillow"]',
                    '.ds-listing-details-chip:contains("days")',
                    '.data-list-txt:contains("Listed")',
                    '.data-list-txt:contains("on Zillow")'
                ]
                
                for selector in dom_selectors:
                    dom_elem = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if dom_elem:
                        dom_text = dom_elem[0].text.strip()
                        # Extract just the number of days
                        import re
                        days_match = re.search(r'(\d+)\s+day', dom_text)
                        if days_match:
                            listing_data['days_on_market'] = days_match.group(1)
                            logging.info(f"✓ Successfully found days on market: {listing_data['days_on_market']}")
                            break
            except Exception as e:
                logging.warning(f"✗ Failed to extract days on market: {str(e)}")
            
            # Extract agent information
            try:
                agent_selectors = [
                    '[data-testid="attribution-AGENT"]',
                    '.ds-listing-agent-information-name',
                    '.agent-info-card',
                    '.agent-info-block'
                ]
                
                for selector in agent_selectors:
                    agent_elem = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if agent_elem:
                        listing_data['agent_name'] = agent_elem[0].text.strip()
                        logging.info(f"✓ Successfully found agent name: {listing_data['agent_name']}")
                        break
            except Exception as e:
                logging.warning(f"✗ Failed to extract agent name: {str(e)}")
            
            # Check if we have at least the basic data
            if listing_data['price'] and listing_data['address']:
                logging.info("✓ Successfully extracted essential listing data")
                return listing_data
            else:
                logging.warning("✗ Failed to extract essential listing data (price or address missing)")
                return None
                
        except Exception as e:
            logging.error(f"Error extracting listing data: {str(e)}")
            return None

    def save_listing_to_csv(self, data, zipcode):
        """Save a single listing to the CSV file"""
        # Extract zipcode from address (last 5 digits)
        address = data.get('address', '')
        zipcode_from_address = address[-5:] if address and address[-5:].isdigit() else ''
        
        with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            row_data = {field: data.get(field.lower(), '') for field in self.fieldnames}
            row_data['ZIPCODE'] = zipcode_from_address
            writer.writerow(row_data)
        logging.info(f"Saved listing data to {self.output_file}")

    def get_listing_urls(self):
        """Get all listing URLs from the search results page, including pagination"""
        urls = []
        page = 1
        has_next_page = True
        base_url = self.driver.current_url

        while has_next_page:
            logging.info(f"Collecting listings from page {page}")
            if page > 1:
                # Construct and navigate to the next page URL
                if '?' in base_url:
                    page_url = f"{base_url}&page={page}"
                else:
                    page_url = f"{base_url}?page={page}"
                self.driver.get(page_url)
                time.sleep(2 + random.random() * 2)  # Random delay between pages
                # Check for "Press and Hold" bot check
                self.handle_press_and_hold_check()

            # Wait for the grid to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="grid-search-results"]'))
                )
            except Exception as e:
                logging.error(f"Grid not found on page {page}: {str(e)}")
                break

            # Scroll to load all listings
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1 + random.random())

            # Get all listings on current page
            grid = self.driver.find_elements(By.XPATH, '//*[@id="grid-search-results"]')
            if grid:
                listings = grid[0].find_elements(By.CSS_SELECTOR, 'ul > li')
                logging.info(f"Found {len(listings)} listings using selector: #grid-search-results > ul > li")
                page_urls = []
                for listing in listings:
                    try:
                        link_selectors = [
                            'a[data-test="property-card-link"]',
                            'a[tabindex="0"]',
                            'a.property-card-link',
                            'a[href*="/homedetails/"]'
                        ]
                        link = None
                        for link_selector in link_selectors:
                            try:
                                links = listing.find_elements(By.CSS_SELECTOR, link_selector)
                                if links:
                                    link = links[0]
                                    break
                            except:
                                continue
                        if link:
                            url = link.get_attribute('href')
                            if url and '/homedetails/' in url and url not in urls:
                                page_urls.append(url)
                        else:
                            logging.debug(f"No valid link found in listing {len(urls) + len(page_urls) + 1}")
                    except Exception as e:
                        logging.warning(f"Could not get URL from listing card: {str(e)}")
                        continue
                if page_urls:
                    urls.extend(page_urls)
                    logging.info(f"Found {len(page_urls)} new listings on page {page}")
                else:
                    logging.info(f"No new listings found on page {page}")
                    break

                # Check for next page button
                next_button_selectors = [
                    "//button[@title='Next page']",
                    "//a[@title='Next page']",
                    "//button[contains(@class, 'next-page')]",
                    "//button[contains(text(), 'Next')]"
                ]
                has_next_page = False
                for selector in next_button_selectors:
                    try:
                        next_buttons = self.driver.find_elements(By.XPATH, selector)
                        if next_buttons and not next_buttons[0].get_attribute('disabled'):
                            has_next_page = True
                            break
                    except:
                        continue
                if not has_next_page:
                    logging.info("No more pages available")
                    break
                page += 1
                time.sleep(1 + random.random())  # Small delay before next page
            else:
                logging.warning(f"No listings grid found on page {page}")
                break
        logging.info(f"Total unique listings found across {page} pages: {len(urls)}")
        return urls
        
        # Store search results URL for backup
        search_url = self.driver.current_url
        processed_urls = set()  # Track processed URLs to avoid duplicates
        
        for idx, listing_url in enumerate(urls, 1):
            if listing_url in processed_urls:
                logging.info(f"Skipping already processed listing: {listing_url}")
                continue
                
            try:
                logging.info(f"Processing listing {idx}/{total_listings}: {listing_url}")
                
                # Navigate to listing in the same window
                try:
                    self.driver.get(listing_url)
                    # Add random delay with natural scrolling
                    time.sleep(1 + random.random())
                    
                    # Check for "Press and Hold" bot check
                    self.handle_press_and_hold_check()
                    
                    scroll_amount = random.randint(100, 300)
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                    time.sleep(1 + random.random())
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    
                    # Check if page loaded successfully
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    logging.info("Successfully loaded listing page")
                except Exception as e:
                    logging.error(f"Failed to load listing: {str(e)}")
                    if "ERR_TOO_MANY_REQUESTS" in str(e) or "ERR_NETWORK" in str(e):
                        logging.warning("Possible rate limiting, taking a longer break...")
                        time.sleep(30 + random.random() * 30)
                        continue
                
                # Get zipcode from the URL
                current_zipcode = listing_url.split('/')[-2].split('-')[-1].split('_')[0]
                
                # Check if page is actually loaded
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    # Verify we're on a listing page by checking for key elements
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="price"]'))
                    )
                except Exception as e:
                    logging.error(f"Page did not load properly: {str(e)}")
                    raise
                
                # Initialize listing data dictionary and tracking
                listing_data = {
                    'zipcode': current_zipcode,
                    'url': listing_url
                }
                
                # Initialize scraping status tracking
                scraping_status = {
                    'mls': False,
                    'price': False,
                    'address': False,
                    'beds': False,
                    'baths': False,
                    'sqft': False,
                    'agent_name': False,
                    'agent_phone': False,
                    'days_on_market': False
                }
                
                # Simulate natural viewing behavior
                scroll_positions = [300, 600, 900, 300, 0]  # Scroll down and back up
                for position in scroll_positions:
                    self.driver.execute_script(f"window.scrollTo(0, {position});")
                    time.sleep(0.5 + random.random())
                
                # Extract MLS number
                try:
                    mls_selectors = [
                        "//*[contains(text(),'MLS#')]",
                        "//span[contains(text(),'MLS')]",
                        "//div[contains(@class, 'mls')]"
                    ]
                    for selector in mls_selectors:
                        mls_elems = self.driver.find_elements(By.XPATH, selector)
                        if mls_elems:
                            listing_data['mls'] = mls_elems[0].text.replace('MLS#', '').replace(':', '').strip()
                            if listing_data['mls']:
                                logging.info(f"✓ Successfully found MLS#: {listing_data['mls']}")
                                scraping_status['mls'] = True
                            break
                except Exception as e:
                    logging.warning(f"✗ Failed to extract MLS#: {str(e)}")
                    listing_data['mls'] = ''
                
                if not scraping_status['mls']:
                    logging.warning("✗ MLS# not found with any selector")
                
                # Extract price
                try:
                    price_selectors = [
                        '[data-testid="price"] span',
                        '.price-text',
                        '[data-testid="home-info"] .price-text'
                    ]
                    for selector in price_selectors:
                        price_elem = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if price_elem:
                            listing_data['price'] = price_elem[0].text.strip()
                            if listing_data['price']:
                                logging.info(f"✓ Successfully found price: {listing_data['price']}")
                                scraping_status['price'] = True
                            break
                except Exception as e:
                    logging.warning(f"✗ Failed to extract price: {str(e)}")
                    listing_data['price'] = ''
                
                if not scraping_status['price']:
                    logging.warning("✗ Price not found with any selector")
                
                # Extract address
                try:
                    address_selectors = [
                        'div.styles__AddressWrapper-fshdp-8-111-1__sc-13x5vko-0 h1.Text-c11n-8-111-1__sc-aiai24-0',
                        '.jDtXfP h1.hZAvJt',  # Using the specific classes from the example
                        '[data-testid="home-info"] h1'  # Keeping one old selector as fallback
                    ]
                    for selector in address_selectors:
                        address_elem = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if address_elem:
                            listing_data['address'] = address_elem[0].text.strip().replace('\xa0', ' ')  # Replace &nbsp;
                            if listing_data['address']:
                                logging.info(f"✓ Successfully found address: {listing_data['address']}")
                                scraping_status['address'] = True
                            break
                except Exception as e:
                    logging.warning(f"✗ Failed to extract address: {str(e)}")
                
                if not scraping_status['address']:
                    logging.warning("✗ Address not found with any selector")
                
                # Initialize values for features we'll scrape later
                beds = ''
                baths = ''
                sqft = ''
                
                try:
                    # Find the container that holds all bed/bath/sqft info
                    container = self.driver.find_element(By.CSS_SELECTOR, 'div[data-testid="bed-bath-sqft-facts"]')
                    
                    # Find all fact containers within the main container
                    fact_containers = container.find_elements(By.CSS_SELECTOR, 'div[data-testid="bed-bath-sqft-fact-container"]')
                    
                    # Process each container
                    for fact_container in fact_containers:
                        try:
                            # Get the value and description text
                            value = fact_container.find_element(By.CSS_SELECTOR, 'span.styles__StyledValueText-fshdp-8-111-1__sc-12ivusx-1').text.strip()
                            desc = fact_container.find_element(By.CSS_SELECTOR, 'span.styles__StyledDescriptionText-fshdp-8-111-1__sc-12ivusx-2').text.strip().lower()
                            
                            # Assign value based on description
                            if 'bed' in desc:
                                beds = value
                                logging.info(f"✓ Successfully found beds: {beds}")
                                scraping_status['beds'] = True
                            elif 'bath' in desc:
                                baths = value
                                logging.info(f"✓ Successfully found baths: {baths}")
                                scraping_status['baths'] = True
                            elif 'sqft' in desc:
                                sqft = value
                                logging.info(f"✓ Successfully found sqft: {sqft}")
                                scraping_status['sqft'] = True
                        except Exception as e:
                            logging.debug(f"Failed to process fact container: {str(e)}")
                            continue
                        except Exception as e:
                                                    logging.debug(f"Failed to process fact container: {str(e)}")
                                                    continue
                except Exception as e:
                    logging.warning(f"Error extracting bed/bath/sqft info: {str(e)}")
                    
                # Log any missing values
                if not beds:
                    logging.warning("✗ Beds not found")
                if not baths:
                    logging.warning("✗ Baths not found")
                if not sqft:
                    logging.warning("✗ Sqft not found")
                    
                    # Beds scraping logic has been removed
                    # New logic will be added when you provide the updated selectors
                    
                    # Search for baths using exact class structure
                    bath_selectors = [
                        'span.Text-c11n-8-111-1__sc-aiai24-0.hZAvJt:contains("Bathrooms:")',  # Primary selector matching the exact HTML
                        '.hZAvJt:contains("Bathrooms")',  # Simplified fallback
                        '[data-testid="facts-list"] span:contains("Bathrooms")'  # Additional fallback
                    ]
                    
                    for selector in bath_selectors:
                        try:
                            bath_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                            bath_text = bath_elem.text.strip()
                            if bath_text:
                                # Extract number after "Bathrooms: " exactly as shown in the HTML
                                bath_match = re.search(r'Bathrooms:\s*(\d+(?:\.\d+)?)', bath_text)
                                if bath_match:
                                    baths = bath_match.group(1)
                                    logging.info(f"✓ Successfully found baths from exact match: {baths}")
                                    scraping_status['baths'] = True
                                
                                if baths:
                                    logging.info(f"✓ Successfully found baths: {baths}")
                                    scraping_status['baths'] = True
                                    break
                        except Exception as e:
                            logging.debug(f"Bath selector {selector} failed: {str(e)}")
                            continue
                    
                    # Third attempt - search for sqft
                    sqft_selectors = [
                        '[data-testid="bed-bath-sqft-fact-container"] .styles__StyledValueText-fshdp-8-111-1__sc-12ivusx-1.hZAvJt.hCiIMl.--medium:last-child',
                        'div[data-testid="bed-bath-sqft-fact-container"]:has(span:contains("sqft"))',
                        'span.Text-c11n-8-111-1__sc-aiai24-0.styles__StyledValueText-fshdp-8-111-1__sc-12ivusx-1.hZAvJt.hCiIMl.--medium'
                    ]
                    
                    for selector in sqft_selectors:
                        try:
                            sqft_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                            sqft_text = sqft_elem.text.strip()
                            if sqft_text and ('sqft' in sqft_text.lower() or sqft_text.replace(',', '').isdigit()):
                                sqft = ''.join(filter(lambda x: x.isdigit() or x == ',', sqft_text))
                                if sqft:
                                    logging.info(f"✓ Successfully found sqft: {sqft}")
                                    scraping_status['sqft'] = True
                                    break
                        except Exception as e:
                            logging.debug(f"Sqft selector {selector} failed: {str(e)}")
                            continue
                    
                    # Fallback methods if initial selectors fail
                    
                    # Fallback for beds
                    if not beds:
                        bed_fallback_selectors = [
                            'div[data-testid="facts-list"] span:contains("Bedroom")',
                            '.home-facts span:contains("bed")',
                            '.fact-list span:contains("Bed")'
                        ]
                        
                        for selector in bed_fallback_selectors:
                            try:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                for elem in elements:
                                    text = elem.text.lower()
                                    bed_match = re.search(r'(\d+)(?:\s*bed|\s*bedroom)s?', text)
                                    if bed_match:
                                        beds = bed_match.group(1)
                                        logging.info(f"✓ Found beds using fallback: {beds}")
                                        scraping_status['beds'] = True
                                        break
                            except Exception as e:
                                logging.debug(f"Bed fallback selector {selector} failed: {str(e)}")
                                continue
                    
                    # Fallback for baths
                    if not baths:
                        bath_fallback_selectors = [
                            'div[data-testid="facts-list"] span:contains("Bathroom")',
                            '.home-facts span:contains("bath")',
                            '.fact-list span:contains("Bath")'
                        ]
                        
                        for selector in bath_fallback_selectors:
                            try:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                for elem in elements:
                                    text = elem.text.lower()
                                    bath_match = re.search(r'(\d+(?:\.\d+)?)(?:\s*bath|\s*bathroom)s?', text)
                                    if bath_match:
                                        baths = bath_match.group(1)
                                        logging.info(f"✓ Found baths using fallback: {baths}")
                                        scraping_status['baths'] = True
                                        break
                            except Exception as e:
                                logging.debug(f"Bath fallback selector {selector} failed: {str(e)}")
                                continue
                    
                    # Fallback for sqft
                    if not sqft:
                        sqft_fallback_selectors = [
                            'div[data-testid="facts-list"] span:contains("Square Feet")',
                            'div[data-testid="facts-list"] span:contains("sqft")',
                            '.home-facts span:contains("sq ft")'
                        ]
                        
                        for selector in sqft_fallback_selectors:
                            try:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                for elem in elements:
                                    text = elem.text.strip()
                                    sqft_match = re.search(r'([\d,]+)(?:\s*sq\.?\s*ft\.?|\s*square\s*feet)', text.lower())
                                    if sqft_match:
                                        sqft = sqft_match.group(1)
                                        logging.info(f"✓ Found sqft using fallback: {sqft}")
                                        scraping_status['sqft'] = True
                                        break
                            except Exception as e:
                                logging.debug(f"Sqft fallback selector {selector} failed: {str(e)}")
                                continue
                    
                    # Last attempt - search all text elements for patterns
                    if not (beds and baths and sqft):
                        # Search all text elements on the page
                        text_elements = self.driver.find_elements(By.CSS_SELECTOR, '[class*="Text-"]')
                        for elem in text_elements:
                            try:
                                text = elem.text.strip().lower()
                                
                                # Look for beds
                                if not beds and ('bed' in text or 'bd' in text):
                                    bed_match = re.search(r'(\d+)(?:\s*bed|\s*bd|\s*br)s?', text)
                                    if bed_match:
                                        beds = bed_match.group(1)
                                        logging.info(f"✓ Found beds in text search: {beds}")
                                        scraping_status['beds'] = True
                                
                                # Look for baths
                                if not baths and ('bath' in text or 'ba' in text):
                                    bath_match = re.search(r'(\d+(?:\.\d+)?)(?:\s*bath|\s*ba|\s*br)s?', text)
                                    if bath_match:
                                        baths = bath_match.group(1)
                                        logging.info(f"✓ Found baths in text search: {baths}")
                                        scraping_status['baths'] = True
                                
                                # Look for sqft
                                if not sqft and ('sqft' in text or 'sq ft' in text or 'square feet' in text):
                                    sqft_match = re.search(r'([\d,]+)(?:\s*sq\.?\s*ft\.?|\s*square\s*feet)', text)
                                    if sqft_match:
                                        sqft = sqft_match.group(1)
                                        logging.info(f"✓ Found sqft in text search: {sqft}")
                                        scraping_status['sqft'] = True
                                
                                if beds and baths and sqft:
                                    break
                            except Exception:
                                continue
                    
                    # Third attempt - look for specific fact labels
                    if not (beds and baths and sqft):
                        fact_selectors = [
                            '[data-testid="facts-list"]',
                            '.home-facts-at-a-glance',
                            '.fact-list',
                            '.property-facts'
                        ]
                        
                        for selector in fact_selectors:
                            try:
                                facts = self.driver.find_element(By.CSS_SELECTOR, selector)
                                facts_text = facts.text.lower()
                                
                                # Look for patterns in the facts text
                                if not beds:
                                    bed_match = re.search(r'(?:^|\D)(\d+\.?\d*)\s*(?:bed|bdrm|bedroom)s?(?:\D|$)', facts_text)
                                    if bed_match:
                                        beds = bed_match.group(1)
                                        logging.info(f"✓ Successfully found beds (facts method): {beds}")
                                        scraping_status['beds'] = True
                                        
                                if not baths:
                                    bath_match = re.search(r'(?:^|\D)(\d+\.?\d*)\s*(?:bath|bth|bathroom)s?(?:\D|$)', facts_text)
                                    if bath_match:
                                        baths = bath_match.group(1)
                                        logging.info(f"✓ Successfully found baths (facts method): {baths}")
                                        scraping_status['baths'] = True
                                        
                                if not sqft:
                                    sqft_match = re.search(r'(?:^|\D)(\d+(?:,\d{3})*)\s*(?:sq\.?\s*ft\.?|square\s*feet|sqft)(?:\D|$)', facts_text)
                                    if sqft_match:
                                        sqft = sqft_match.group(1)
                                        logging.info(f"✓ Successfully found square footage (facts method): {sqft}")
                                        scraping_status['sqft'] = True
                                
                                if beds and baths and sqft:
                                    break
                                    
                            except Exception as e:
                                logging.debug(f"Facts selector {selector} failed: {str(e)}")
                                continue
                                
                    # Second attempt - using summary container
                    if not (beds and baths):
                        summary_selectors = [
                            '[data-testid="home-summary-stats"]',
                            '.summary-container',
                            '[data-testid="home-details"]'
                        ]
                        
                        for selector in summary_selectors:
                            try:
                                summary = self.driver.find_element(By.CSS_SELECTOR, selector)
                                summary_text = summary.text.lower()
                                
                                # Look for patterns like "2 bd", "2 beds", "2 ba", "2 baths"
                                import re
                                bed_match = re.search(r'(\d+\.?\d*)\s*(?:bd|bed|beds|bedroom|bedrooms)', summary_text)
                                bath_match = re.search(r'(\d+\.?\d*)\s*(?:ba|bath|baths|bathroom|bathrooms)', summary_text)
                                sqft_match = re.search(r'(\d+,?\d*)\s*(?:sq\s*ft|sqft|square\s*feet)', summary_text)
                                
                                if bed_match and not beds:
                                    beds = bed_match.group(1)
                                    logging.info(f"✓ Successfully found beds (method 2): {beds}")
                                    scraping_status['beds'] = True
                                if bath_match and not baths:
                                    baths = bath_match.group(1)
                                    logging.info(f"✓ Successfully found baths (method 2): {baths}")
                                    scraping_status['baths'] = True
                                if sqft_match and not sqft:
                                    sqft = sqft_match.group(1)
                                    logging.info(f"✓ Successfully found square footage (method 2): {sqft}")
                                    scraping_status['sqft'] = True
                                    
                                if beds and baths:
                                    break
                            except Exception:
                                continue
                    
                # Initialize agent information
                listed_by = ''
                phone = ''
                try:
                    # Find agent name and phone from attribution section
                    agent_selectors = [
                        'p[data-testid="attribution-LISTING_AGENT"]',
                        'div.SellerAttributionStyles__StyledListedBy-fshdp-8-111-1__sc-5b3vve-0 p'
                    ]
                    
                    for selector in agent_selectors:
                        try:
                            agent_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                            # Get all text spans within the agent element
                            spans = agent_elem.find_elements(By.CSS_SELECTOR, 'span.Text-c11n-8-111-1__sc-aiai24-0')
                            
                            if spans:
                                # First span should be agent name
                                listed_by = spans[0].text.strip()
                                if listed_by:
                                    scraping_status['agent_name'] = True
                                    logging.info(f"✓ Successfully found agent name: {listed_by}")
                                
                                # Second span should contain phone number
                                if len(spans) > 1:
                                    phone = spans[1].text.strip().rstrip(',')  # Remove trailing comma
                                    if phone:
                                        scraping_status['agent_phone'] = True
                                        logging.info(f"✓ Successfully found agent phone: {phone}")
                                break
                        except Exception as e:
                            logging.debug(f"Agent info extraction failed with selector {selector}: {str(e)}")
                            continue

                    # Fallback selectors for agent information
                    if not listed_by or not phone:
                        fallback_selectors = [
                            'div.SellerAttributionStyles__StyledListedBy-fshdp-8-111-1__sc-5b3vve-0',
                            'div[data-testid="attribution-LISTING_AGENT"]'
                        ]
                    
                    if not listed_by or not phone:
                        for selector in fallback_selectors:
                            try:
                                container = self.driver.find_element(By.CSS_SELECTOR, selector)
                                content = container.text.strip()
                                
                                # Try to find name if not already found
                                if not listed_by:
                                    name_match = re.search(r'^([^0-9,]+?)(?:\s*\d|$)', content)
                                    if name_match:
                                        listed_by = name_match.group(1).strip()
                                        scraping_status['agent_name'] = True
                                        logging.info(f"✓ Successfully found agent name (fallback): {listed_by}")
                                
                                # Try to find phone if not already found
                                if not phone:
                                    phone_match = re.search(r'(\d{3}[- ]?\d{3}[- ]?\d{4})', content)
                                    if phone_match:
                                        phone = phone_match.group(1).strip()
                                        scraping_status['agent_phone'] = True
                                        logging.info(f"✓ Successfully found agent phone (fallback): {phone}")
                                
                                if listed_by and phone:
                                    break
                            except Exception as e:
                                logging.debug(f"Fallback agent info extraction failed with selector {selector}: {str(e)}")
                                continue
                            
                    listing_data['agent_name'] = listed_by
                    listing_data['agent_phone'] = phone
                    
                except Exception as e:
                    logging.warning(f"Could not extract agent info: {str(e)}")
                    
                # All phone number scraping logic has been removed
                # New logic will be added when you provide the updated selectors
                
                # Initialize days on market
                days = ''
                try:
                    dom_selectors = [
                        'dl.styles__StyledOverviewStats-fshdp-8-111-1__sc-1x11gd9-0 dt:first-child strong',  # Primary selector
                        'dl.kpgmGL dt:first-child strong'  # Backup using class name
                    ]
                    
                    for selector in dom_selectors:
                        try:
                            dom_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                            # Verify this is the "on Zillow" stat by checking the label
                            label_elem = dom_elem.find_element(By.XPATH, '../following-sibling::dt')
                            if 'on zillow' in label_elem.text.lower():
                                days = dom_elem.text.strip()
                                if days:
                                    scraping_status['days_on_market'] = True
                                    logging.info(f"✓ Successfully found days on market: {days}")
                                    break
                        except Exception as e:
                            logging.debug(f"DOM selector {selector} failed: {str(e)}")
                            continue
                except Exception as e:
                    logging.warning(f"Could not extract days on market: {str(e)}")
                listing_data['days_on_market'] = days

                # Update the listing data with scraped values
                listing_data.update({
                    'beds': beds,
                    'baths': baths,
                    'sqft': sqft,
                    'agent_name': listed_by,
                    'agent_phone': phone,
                    'days_on_market': days
                })

                # Create Google Maps URL if we have an address
                if listing_data.get('address'):
                    listing_data['maps_url'] = f"https://www.google.com/maps/search/{listing_data['address'].replace(' ', '+')}"
                else:
                    listing_data['maps_url'] = ''
                
                # Log scraping summary for this listing
                logging.info("\n=== Scraping Summary ===")
                total_fields = len(scraping_status)
                successful_fields = sum(1 for status in scraping_status.values() if status)
                logging.info(f"Successfully scraped {successful_fields}/{total_fields} fields")
                
                # Log details for each field
                for field, success in scraping_status.items():
                    status_symbol = "✓" if success else "✗"
                    value = listing_data.get(field, '')
                    if success:
                        logging.info(f"{status_symbol} {field}: {value}")
                    else:
                        logging.warning(f"{status_symbol} {field}: Not found")
                
                logging.info("=====================")
                
                # Save the listing to CSV
                self.save_listing_to_csv(listing_data, self.current_zipcode)
                logging.info(f"Successfully saved listing data to CSV for {listing_data.get('address', 'Unknown Address')}")

                if self.stop_after_first:
                    logging.info("Stop after first listing flag is set. Stopping scraper but keeping browser open.")
                    # Keep the browser window open at the current listing
                    return True  # Return True to indicate successful scraping

                # Return to search results page
                self.driver.get(search_url)
                time.sleep(3 + random.random() * 2)  # Longer delay when returning to search page
                
                # Wait for the grid to be visible again
                try:
                    wait = WebDriverWait(self.driver, 10)
                    wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="grid-search-results"]')))
                except Exception as e:
                    logging.warning(f"Could not verify search results page loaded: {str(e)}")
                    # Try to refresh the page
                    self.driver.refresh()
                    time.sleep(5)

            except Exception as e:
                logging.error(f"Error processing listing: {str(e)}")
                
                # Determine if it's a recoverable error
                if "ERR_TOO_MANY_REQUESTS" in str(e) or "ERR_NETWORK" in str(e):
                    logging.warning("Rate limiting detected, taking a cooling break...")
                    time.sleep(60 + random.random() * 30)  # Long cooling period
                else:
                    time.sleep(5 + random.random() * 5)  # Shorter break for other errors
                
                # Try to recover by going back to search results
                try:
                    self.driver.get(search_url)
                    time.sleep(5)  # Wait for search page to load
                    
                    # Verify we're back on search page
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "grid-search-results"))
                    )
                    logging.info("Successfully recovered to search page")
                except Exception as nav_error:
                    logging.error(f"Could not recover to search page: {str(nav_error)}")
                    
                if self.stop_after_first:
                    return False  # Return False to indicate error
                continue
                
            # Track progress
            processed = len(processed_urls) if 'processed_urls' in locals() else idx
            logging.info(f"Progress: {processed}/{total_listings} listings processed")

    def handle_press_and_hold_check(self, max_attempts=3):
        """Handle the Zillow Press & Hold verification check.

        This method detects and handles the Zillow bot verification dialog that requires
        pressing and holding a button to prove human interaction.

        Args:
            max_attempts: Maximum number of attempts to complete the verification

        Returns:
            bool: True if verification was successful, False otherwise
        """
        for attempt in range(max_attempts):
            try:
                # Look for the verification button
                try:
                    # Look for the exact Press & Hold element using ID and class
                    button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "p#uQlxAoLpWLaeQTc.mLimfKWklvcZMZk"))
                    )

                    if not button.is_displayed() or not button.is_enabled():
                        logging.info("No Press & Hold verification needed")
                        return True
                except TimeoutException:
                    # No verification needed
                    return True

                logging.info("Found Press & Hold verification, attempting to complete...")

                # Create action chain with human-like behavior
                actions = ActionChains(self.driver)

                # Add slight random offset to mouse position
                offset_x = random.randint(-5, 5)
                offset_y = random.randint(-3, 3)

                # Random hold duration between 3-4 seconds
                hold_duration = 3 + random.random()

                # Perform the verification with natural movement
                actions.move_to_element_with_offset(button, offset_x, offset_y)
                actions.pause(0.3 + random.random() * 0.5)  # Natural pause
                actions.click_and_hold()
                actions.pause(hold_duration)
                actions.release()
                actions.perform()

                # Wait for verification to complete
                time.sleep(1.5 + random.random())

                # Check if verification was successful
                try:
                    WebDriverWait(self.driver, 5).until_not(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "p#uQlxAoLpWLaeQTc"))
                    )
                    logging.info("Successfully completed Press & Hold verification")
                    return True
                except TimeoutException:
                    if attempt < max_attempts - 1:
                        logging.warning(f"Press and hold attempt {attempt + 1} failed, retrying...")
                        time.sleep(2 + random.random())

            except Exception as e:
                logging.error(f"Error during press and hold verification: {str(e)}")
                if attempt < max_attempts - 1:
                    time.sleep(2 + random.random())

        logging.error("Failed all attempts at Press & Hold verification")
        return False

    def perform_mouse_hold(self, element, hold_duration=1.0):
        """
        Performs a mouse press and hold action on a specified element.
        
        Args:
            element: The web element to perform the action on
            hold_duration: How long to hold the mouse button down in seconds (default 1.0 second)
        """
        try:
            # Create ActionChains instance
            actions = ActionChains(self.driver)
            
            # Move to the element first (with a slight random offset to appear more human-like)
            offset_x = random.randint(-10, 10)
            offset_y = random.randint(-10, 10)
            actions.move_to_element_with_offset(element, offset_x, offset_y)
            
            # Perform the click and hold
            actions.click_and_hold()
            actions.pause(hold_duration)  # Hold for specified duration
            actions.release()
            
            # Execute the action chain
            actions.perform()
            
            logging.info(f"Successfully performed mouse hold for {hold_duration} seconds")
            return True
            
        except Exception as e:
            logging.error(f"Error performing mouse hold: {str(e)}")
            return False
            
    def perform_mouse_hold_at_coordinates(self, x, y, hold_duration=1.0):
        """
        Performs a mouse press and hold action at specific coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            hold_duration: How long to hold the mouse button down in seconds (default 1.0 second)
        """
        try:
            # Create ActionChains instance
            actions = ActionChains(self.driver)
            
            # Move to the specific coordinates
            actions.move_by_offset(x, y)
            
            # Perform the click and hold
            actions.click_and_hold()
            actions.pause(hold_duration)  # Hold for specified duration
            actions.release()
            
            # Execute the action chain
            actions.perform()
            
            logging.info(f"Successfully performed mouse hold at coordinates ({x}, {y}) for {hold_duration} seconds")
            return True
            
        except Exception as e:
            logging.error(f"Error performing mouse hold at coordinates: {str(e)}")
            return False

    def close(self):
        logging.info("Closing browser...")
        try:
            self.driver.quit()
            logging.info("Browser closed successfully")
        except Exception as e:
            logging.error(f"Error closing browser: {str(e)}")
            logging.error(f"Error closing browser: {str(e)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Zillow Scraper')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--stop-after-first', action='store_true', help='Stop after scraping first listing (for testing)')
    parser.add_argument('--min-price', type=int, default=200000, help='Minimum price filter')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries per listing')
    args = parser.parse_args()

    logging.info("Starting Zillow scraper...")
    
    # Initialize Chrome options
    options = uc.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--enable-javascript")
    
    if args.headless:
        logging.info("Running in headless mode")
        options.add_argument('--headless=new')  # Use the new headless mode
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')
        # Add additional options to make headless more stable
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--remote-debugging-port=9222')
        # Set a more realistic user agent
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.7258.155 Safari/537.36')
    else:
        options.add_argument('--start-maximized')
        
    # Create the scraper instance with our options
    bot = ZillowScraper(options)
    bot.stop_after_first = args.stop_after_first
    
    try:
        # Only stop after first listing if the flag is set via command line
        bot.stop_after_first = args.stop_after_first
        
        for zipcode in ZIPCODES:
            logging.info(f"Processing zipcode: {zipcode}")
            retry_count = 0
            success = False
            
            while retry_count < args.max_retries and not success:
                try:
                    bot.search_zipcode(zipcode)
                    bot.scrape_listings()
                    success = True
                except Exception as e:
                    retry_count += 1
                    logging.error(f"Error processing zipcode {zipcode} (attempt {retry_count}/{args.max_retries}): {str(e)}")
                    if retry_count < args.max_retries:
                        logging.info(f"Retrying zipcode {zipcode} in 10 seconds...")
                        time.sleep(10)
                    else:
                        logging.error(f"Failed to process zipcode {zipcode} after {args.max_retries} attempts")
            
            if bot.stop_after_first:
                break
            
            # Random delay between zipcodes
            delay = random.uniform(20, 40)
            logging.info(f"Waiting {delay:.1f} seconds before next zipcode...")
            time.sleep(delay)

    except KeyboardInterrupt:
        logging.info("Scraper stopped by user")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
    finally:
        bot.close()
