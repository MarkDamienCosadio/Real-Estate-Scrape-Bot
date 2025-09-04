import time
import random
import os
import csv
import re
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
    def __init__(self, options=None, max_listings=0):
        logging.info("Initializing ZillowScraper...")

        # Create timestamp for the output file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.output_file = 'zillow_results.csv'
        logging.info(f"Output will be saved to: {self.output_file}")
        
        # Track the current zipcode
        self.current_zipcode = None

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
        self.max_listings = max_listings  # Number of listings to process (0 means no limit)
        self.current_zipcode = None
        logging.info(f"ZillowScraper initialized successfully. Max listings per zipcode: {max_listings if max_listings > 0 else 'No limit'}")

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
            
    def sort_by_newest(self):
        """Sort listings by newest first"""
        logging.info("Attempting to sort listings by newest first")
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
                
            # Click the "Newest" option
            sort_option_selectors = [
                '//button[contains(text(), "Newest")]',
                '//button[contains(@aria-label, "Newest")]',
                '//li[contains(text(), "Newest")]',
                '//div[contains(text(), "Newest")]',
                '//span[contains(text(), "Newest")]'
            ]
            
            sort_option = None
            for selector in sort_option_selectors:
                try:
                    sort_option = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    sort_option.click()
                    time.sleep(3)  # Wait for sorting to take effect
                    logging.info(f"Selected 'Newest' option using selector: {selector}")
                    return True
                except Exception:
                    continue
                    
            if not sort_option:
                logging.warning("Could not find 'Newest' option with any selector")
                return False
                
        except Exception as e:
            logging.error(f"Error sorting listings by newest: {str(e)}")
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
        
        # Sort listings by newest first
        logging.info("Sorting listings by newest first")
        self.sort_by_newest()
        
        # Count listings found
        listing_count = self.count_listings()
        logging.info(f"Found {listing_count} listings in search results")
        
        # Process listings
        logging.info("Starting to process listings")
        self.process_all_listings(self.max_listings)
        
    def count_listings(self):
        """Count the number of listings in the search results"""
        logging.info("Counting listings in search results")
        wait = WebDriverWait(self.driver, 10)
        
        try:
            # Wait for page to fully load and render all listings
            time.sleep(5)
            
            # More specific selectors focusing on li elements within containers
            listing_selectors = [
                '//ul[contains(@class, "photo-cards")]/li',
                '//div[contains(@id, "search-results")]//li',
                '//div[contains(@class, "search-results")]//li',
                '//div[contains(@class, "result-list")]//li',
                '//ul[contains(@class, "List")]//li',
                '//div[@data-testid="search-result-list"]//li',
                '//main//ul//li[contains(@class, "ListItem")]',
                '//main//div[contains(@class, "StyledPropertyCardDataWrapper")]',
                '//section//ul//li[.//a[contains(@class, "property-card")]]'
            ]
            
            for selector in listing_selectors:
                try:
                    # Find all elements matching the selector
                    listings = self.driver.find_elements(By.XPATH, selector)
                    
                    if listings and len(listings) > 0:
                        count = len(listings)
                        # Only return if we found a reasonable number of listings
                        if count > 5:
                            logging.info(f"Found {count} listings using selector: {selector}")
                            return count
                        else:
                            logging.debug(f"Found only {count} listings with {selector}, trying other selectors")
                except Exception as e:
                    logging.debug(f"Error with selector {selector}: {str(e)}")
                    continue
            
            # If we're here, check the page source for common patterns
            page_source = self.driver.page_source
            try:
                # Look for text that might indicate the number of listings
                match = re.search(r'(\d+)\s+homes', page_source) or re.search(r'(\d+)\s+results', page_source)
                if match:
                    count = int(match.group(1))
                    logging.info(f"Found {count} listings from page text")
                    return count
            except Exception:
                pass
            
            # If no listings found with any selector
            logging.warning("Could not count listings with provided selectors")
            return 0
                
        except Exception as e:
            logging.error(f"Error counting listings: {str(e)}")
            return 0
    
    def process_all_listings(self, max_listings=0):
        """Process listings on the search results page
        
        Args:
            max_listings: Maximum number of listings to process (0 for all listings)
        """
        if max_listings > 0:
            logging.info(f"Processing up to {max_listings} listings on the page")
        else:
            logging.info("Processing all listings on the page")
            
        wait = WebDriverWait(self.driver, 10)
        processed_urls = set()  # Keep track of already processed URLs to avoid duplicates
        
        try:
            # Get all listing elements
            listing_selectors = [
                # Find all listings with these selectors
                '//div[contains(@class, "property-card")]/a',
                '//ul[contains(@class, "photo-cards")]//li//a[contains(@class, "property-card")]',
                '//li[contains(@class, "ListItem")]//a',
                '//div[contains(@class, "StyledPropertyCardDataWrapper")]//a',
                '//li[contains(@class, "search-result")]//a',
                '//article[contains(@class, "property-card")]//a',
                '//div[contains(@class, "list-card")]//a',
                '//div[@data-test="property-card"]//a'
            ]
            
            # Try each selector until we find listings
            all_listings = []
            for selector in listing_selectors:
                try:
                    listings = self.driver.find_elements(By.XPATH, selector)
                    if len(listings) > 0:
                        all_listings = listings
                        logging.info(f"Found {len(listings)} listings with selector: {selector}")
                        break
                except Exception as e:
                    logging.warning(f"Failed to find listings with selector {selector}: {str(e)}")
            
            if not all_listings:
                logging.warning("Could not find any listings with the provided selectors")
                return False
            
            # Determine how many listings to process
            if max_listings > 0:
                listings_to_process = min(max_listings, len(all_listings))
                logging.info(f"Will process {listings_to_process} out of {len(all_listings)} available listings")
            else:
                listings_to_process = len(all_listings)
                logging.info(f"Will process all {listings_to_process} available listings")
                
            # Process each listing
            processed_count = 0
            for i, listing in enumerate(all_listings):
                # Stop if we've reached the maximum number of listings to process
                if max_listings > 0 and processed_count >= max_listings:
                    logging.info(f"Reached maximum number of listings to process ({max_listings})")
                    break
                    
                try:
                    # Get listing URL before clicking
                    try:
                        listing_url = listing.get_attribute('href')
                        if not listing_url or listing_url in processed_urls:
                            continue  # Skip if no URL or already processed
                        
                        processed_urls.add(listing_url)
                    except Exception as e:
                        logging.warning(f"Could not get URL for listing {i+1}: {str(e)}")
                        continue
                    
                    logging.info(f"Processing listing {i+1}/{listings_to_process}: {listing_url}")
                    
                    # Click to open the listing
                    try:
                        # Store the current window handle
                        main_window = self.driver.current_window_handle
                        
                        # Open in new tab
                        ActionChains(self.driver).key_down(Keys.CONTROL).click(listing).key_up(Keys.CONTROL).perform()
                        
                        # Switch to the new tab
                        wait.until(lambda d: len(d.window_handles) > 1)
                        new_tab = [window for window in self.driver.window_handles if window != main_window][0]
                        self.driver.switch_to.window(new_tab)
                        
                        # Wait for page to load
                        wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
                        time.sleep(3)  # Additional wait to ensure page elements load
                        
                        # Extract data
                        self.extract_listing_data(listing_url)
                        
                        # Close tab and switch back to main window
                        self.driver.close()
                        self.driver.switch_to.window(main_window)
                        
                        # Increment the processed count
                        processed_count += 1
                        
                    except Exception as e:
                        logging.error(f"Error processing listing {i+1}: {str(e)}")
                        # If something goes wrong, make sure we're back at the main window
                        try:
                            self.driver.switch_to.window(main_window)
                        except:
                            pass  # Already on main window or other issue
                
                except Exception as e:
                    logging.error(f"Unexpected error processing listing {i+1}: {str(e)}")
                    # Continue with next listing rather than stopping
            
            return True
                
        except Exception as e:
            logging.error(f"Error processing listings: {str(e)}")
            return False
            
    def open_first_listing(self):
        """Open the first listing in the search results"""
        logging.info("Attempting to open the first listing")
        wait = WebDriverWait(self.driver, 10)
        
        try:
            # Various selectors to find the first listing
            first_listing_selectors = [
                # Put the working selector first
                '//div[contains(@class, "property-card")]/a[1]',
                # Add more generic selectors that might work better
                '//ul[contains(@class, "photo-cards")]/li[1]//a[1]',
                '//li[contains(@class, "ListItem")][1]//a[1]',
                '//div[contains(@class, "StyledPropertyCardDataWrapper")][1]//a[1]',
                # Keep the original selectors as fallbacks
                '//li[contains(@class, "search-result")]//a[1]',
                '//article[contains(@class, "property-card")]//a[1]',
                '//div[contains(@class, "list-card")]//a[1]',
                '//div[@data-test="property-card"]/a[1]'
            ]
            
            first_listing = None
            for selector in first_listing_selectors:
                try:
                    first_listing = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    logging.info(f"Found first listing using selector: {selector}")
                    
                    # Save the listing URL before clicking
                    listing_url = first_listing.get_attribute('href')
                    logging.info(f"First listing URL: {listing_url}")
                    
                    # Click the first listing to open it
                    first_listing.click()
                    logging.info("Successfully clicked on first listing")
                    
                    # Wait for the listing page to load
                    time.sleep(5)
                    
                    # Extract data from the listing page
                    logging.info("Extracting data from listing page")
                    self.extract_listing_data(listing_url)
                    
                    return True
                except Exception as e:
                    logging.warning(f"Failed to click first listing with selector {selector}: {str(e)}")
                    continue
                    
            if not first_listing:
                logging.warning("Could not find any listing with the provided selectors")
                return False
                
        except Exception as e:
            logging.error(f"Error opening first listing: {str(e)}")
            return False
    
    def extract_listing_data(self, listing_url):
        """Extract data from the current listing page"""
        logging.info(f"Extracting data from: {listing_url}")
        wait = WebDriverWait(self.driver, 10)
        
        try:
            # Initialize data dictionary
            data = {
                'ZIPCODE': self.current_zipcode,
                'MLS': '',
                'PRICE': '',
                'ADDRESS': '',
                'BEDS': '',
                'BATHS': '',
                'SQFT': '',
                'URL': listing_url,
                'MAPS_URL': '',
                'DAYS_ON_MARKET': '',
                'AGENT_NAME': '',
                'AGENT_PHONE': ''
            }
            
            # Extract price using the exact selector
            price_selectors = [
                '//span[@data-testid="price"]',
                '//span[@data-testid="price"]/span',
                '//span[contains(@class, "bzMbAh") or contains(@class, "fYrVpn")]',
                # Fallback selectors
                '//span[contains(@class, "Price")]',
                '//*[contains(@class, "price")]',
                '//span[contains(text(), "$")]'
            ]
            
            for selector in price_selectors:
                try:
                    price_elem = self.driver.find_element(By.XPATH, selector)
                    price_text = price_elem.text.strip()
                    if price_text:
                        data['PRICE'] = price_text
                        logging.info(f"Found price: {price_text}")
                        break
                except Exception:
                    continue
            
            # Extract address using the exact selector
            address_selectors = [
                '//h1[contains(@class, "hZAvJt")]',
                '//h1[contains(@class, "Text-c11n-8-111-1__sc-aiai24-0")]',
                # Fallback selectors
                '//h1[@itemprop="address"]',
                '//h1[contains(@class, "Address")]',
                '//span[@data-testid="address"]',
                '//div[contains(@class, "address")]',
                '//h1'
            ]
            
            for selector in address_selectors:
                try:
                    address_elem = self.driver.find_element(By.XPATH, selector)
                    address_text = address_elem.text.strip()
                    if address_text:
                        data['ADDRESS'] = address_text
                        logging.info(f"Found address: {address_text}")
                        break
                except Exception:
                    continue
            
            # Extract beds, baths, sqft using the exact selectors based on the HTML structure
            try:
                # Try to get the whole facts container first
                facts_container = self.driver.find_element(By.XPATH, '//div[@data-testid="bed-bath-sqft-facts"]')
                
                # Extract beds - find the container with "beds" text and get the value
                try:
                    beds_elem = facts_container.find_element(By.XPATH, 
                        './/div[@data-testid="bed-bath-sqft-fact-container"][.//span[contains(text(), "beds")]]//span[contains(@class, "StyledValueText") or contains(@class, "hCiIMl")]')
                    beds_text = beds_elem.text.strip()
                    if beds_text:
                        data['BEDS'] = beds_text
                        logging.info(f"Found beds: {data['BEDS']}")
                except Exception as e:
                    logging.warning(f"Could not extract beds from facts container: {str(e)}")
                
                # Extract baths - find the container with "baths" text and get the value
                try:
                    # This handles both the div and button container cases
                    baths_elem = facts_container.find_element(By.XPATH, 
                        './/*[.//span[contains(text(), "baths")]]//span[contains(@class, "StyledValueText") or contains(@class, "hCiIMl")]')
                    baths_text = baths_elem.text.strip()
                    if baths_text:
                        data['BATHS'] = baths_text
                        logging.info(f"Found baths: {data['BATHS']}")
                except Exception as e:
                    logging.warning(f"Could not extract baths from facts container: {str(e)}")
                
                # Extract sqft - find the container with "sqft" text and get the value
                try:
                    sqft_elem = facts_container.find_element(By.XPATH, 
                        './/div[@data-testid="bed-bath-sqft-fact-container"][.//span[contains(text(), "sqft")]]//span[contains(@class, "StyledValueText") or contains(@class, "hCiIMl")]')
                    sqft_text = sqft_elem.text.strip()
                    if sqft_text:
                        data['SQFT'] = sqft_text.replace(',', '')
                        logging.info(f"Found sqft: {data['SQFT']}")
                except Exception as e:
                    logging.warning(f"Could not extract sqft from facts container: {str(e)}")
                    
            except Exception as e:
                logging.warning(f"Could not find bed-bath-sqft facts container: {str(e)}")
                # Fallback to individual selectors if we can't find the container
                
                # Extract beds - more precise fallback selectors
                beds_selectors = [
                    # Most specific selector based on the HTML structure
                    '//div[@data-testid="bed-bath-sqft-facts"]//div[@data-testid="bed-bath-sqft-fact-container"][.//span[contains(text(), "beds")]]//span[contains(@class, "StyledValueText") or contains(@class, "hCiIMl")]',
                    # Other potential selectors
                    '//span[contains(text(), "beds")]/preceding-sibling::span',
                    '//div[@data-testid="bed-bath-sqft-fact-container"][1]//span[contains(@class, "hCiIMl")]',
                    '//span[contains(@data-testid, "bed")]',
                    '//span[contains(@class, "bed")]'
                ]
                
                for selector in beds_selectors:
                    try:
                        beds_elem = self.driver.find_element(By.XPATH, selector)
                        beds_text = beds_elem.text.strip()
                        if beds_text:
                            data['BEDS'] = beds_text
                            logging.info(f"Found beds (fallback): {data['BEDS']}")
                            break
                    except Exception:
                        continue
                
                # Extract baths - more precise fallback selectors
                baths_selectors = [
                    # Most specific selector based on the HTML structure
                    '//div[@data-testid="bed-bath-sqft-facts"]//*[.//span[contains(text(), "baths")]]//span[contains(@class, "StyledValueText") or contains(@class, "hCiIMl")]',
                    # Handle both button and div cases
                    '//button[.//span[contains(text(), "baths")]]//span[contains(@class, "StyledValueText")]',
                    # Other potential selectors
                    '//span[contains(text(), "baths")]/preceding-sibling::span',
                    '//div[@data-testid="bed-bath-sqft-fact-container"][2]//span[contains(@class, "hCiIMl")]',
                    '//span[contains(@data-testid, "bath")]',
                    '//span[contains(@class, "bath")]'
                ]
                
                for selector in baths_selectors:
                    try:
                        baths_elem = self.driver.find_element(By.XPATH, selector)
                        baths_text = baths_elem.text.strip()
                        if baths_text:
                            data['BATHS'] = baths_text
                            logging.info(f"Found baths (fallback): {data['BATHS']}")
                            break
                    except Exception:
                        continue
                
                # Extract sqft - more precise fallback selectors
                sqft_selectors = [
                    # Most specific selector based on the HTML structure
                    '//div[@data-testid="bed-bath-sqft-facts"]//div[@data-testid="bed-bath-sqft-fact-container"][.//span[contains(text(), "sqft")]]//span[contains(@class, "StyledValueText") or contains(@class, "hCiIMl")]',
                    # Other potential selectors
                    '//div[@data-testid="bed-bath-sqft-fact-container"][.//span[contains(text(), "sqft")]]//span[contains(@class, "StyledValueText")]',
                    '//span[contains(text(), "sqft")]/preceding-sibling::span',
                    '//div[@data-testid="bed-bath-sqft-fact-container"][3]//span[contains(@class, "hCiIMl")]',
                    '//span[contains(@data-testid, "sqft")]',
                    '//span[contains(@class, "sqft")]/preceding-sibling::*'
                ]
                
                for selector in sqft_selectors:
                    try:
                        sqft_elem = self.driver.find_element(By.XPATH, selector)
                        sqft_text = sqft_elem.text.strip()
                        if sqft_text:
                            data['SQFT'] = sqft_text.replace(',', '')
                            logging.info(f"Found sqft (fallback): {data['SQFT']}")
                            break
                    except Exception:
                        continue
                    
            # Extract MLS number using the specific element
            mls_selectors = [
                # Specific selector based on the HTML provided
                '//span[contains(@class, "feqFQg") and contains(text(), "MLS#:")]',
                # Fallback selectors
                '//span[contains(text(), "MLS#")]',
                '//span[contains(text(), "MLS #")]',
                '//span[contains(text(), "MLS:")]',
                '//span[contains(text(), "MLS") and contains(text(), "#")]',
                '//div[contains(text(), "MLS")]'
            ]
            
            for selector in mls_selectors:
                try:
                    mls_elem = self.driver.find_element(By.XPATH, selector)
                    mls_text = mls_elem.text.strip()
                    if mls_text:
                        # Extract just the MLS number - everything after "MLS#:" or "MLS #:" or similar
                        mls_match = re.search(r'MLS#?:?\s*([A-Za-z0-9\-]+)', mls_text)
                        if mls_match:
                            data['MLS'] = mls_match.group(1).strip()
                            logging.info(f"Found MLS: {data['MLS']}")
                            break
                except Exception:
                    continue
                    
            # Extract days on market
            dom_selectors = [
                '//div[contains(text(), "Days on") or contains(text(), "day on")]/span',
                '//span[contains(text(), "Days on") or contains(text(), "day on")]/following-sibling::span',
                '//span[contains(text(), "Listed:")]',
                '//div[contains(text(), "Listed:")]'
            ]
            
            for selector in dom_selectors:
                try:
                    dom_elem = self.driver.find_element(By.XPATH, selector)
                    dom_text = dom_elem.text.strip()
                    if dom_text:
                        # Try to extract just the number
                        dom_match = re.search(r'\d+', dom_text)
                        if dom_match:
                            data['DAYS_ON_MARKET'] = dom_match.group(0)
                            logging.info(f"Found days on market: {data['DAYS_ON_MARKET']}")
                            break
                except Exception:
                    continue
                    
            # Extract agent information using the specific element
            agent_name_selectors = [
                # Most specific selector based on the attribution element
                '//p[@data-testid="attribution-LISTING_AGENT"]/span[1]',
                # Alternative if the structure is slightly different
                '//p[@data-testid="attribution-LISTING_AGENT"]//span[1]',
                # Previous specific selectors
                '//span[contains(@class, "Text-c11n-8-111-1__sc-aiai24-0") and contains(@class, "hZAvJt") and not(contains(text(), "-"))]',
                '//span[contains(@class, "hZAvJt") and string-length() > 5 and not(contains(text(), "-")) and not(contains(text(), "MLS"))]',
                # Fallback selectors
                '//div[contains(@class, "agent-info")]//*[contains(text(), "Agent:")]/../following-sibling::*',
                '//a[contains(@class, "agent-name")]',
                '//a[contains(@href, "agent")]',
                '//div[contains(@class, "agent-name")]',
                '//span[contains(@class, "agent-name")]'
            ]
            
            for selector in agent_name_selectors:
                try:
                    agent_elem = self.driver.find_element(By.XPATH, selector)
                    agent_text = agent_elem.text.strip()
                    # Validate it looks like a name (not a phone number or other info)
                    if (agent_text and len(agent_text) > 3 and  # Avoid empty or too short names
                        not re.search(r'\d{3}-\d{3}-\d{4}', agent_text) and  # Not a phone number
                        not re.search(r'MLS', agent_text)):  # Not MLS info
                        data['AGENT_NAME'] = agent_text
                        logging.info(f"Found agent: {data['AGENT_NAME']}")
                        break
                except Exception:
                    continue
                    
            # Extract agent phone using the specific element
            phone_selectors = [
                # Most specific selector based on the attribution element
                '//p[@data-testid="attribution-LISTING_AGENT"]/span[2]',
                # Alternative if the structure is slightly different
                '//p[@data-testid="attribution-LISTING_AGENT"]//span[contains(text(), "-")]',
                # Previous specific selectors
                '//span[contains(@class, "Text-c11n-8-111-1__sc-aiai24-0") and contains(@class, "hZAvJt") and contains(text(), "-")]',
                '//span[contains(text(), "-") and contains(@class, "hZAvJt")]',
                # Fallback selectors
                '//a[contains(@href, "tel:")]',
                '//span[contains(text(), "Call")]',
                '//button[contains(text(), "Call")]',
                '//div[contains(@class, "phone")]',
                '//span[contains(@class, "phone")]'
            ]
            
            for selector in phone_selectors:
                try:
                    phone_elem = self.driver.find_element(By.XPATH, selector)
                    phone_text = phone_elem.text.strip()
                    if not phone_text and 'href' in phone_elem.get_attribute('outerHTML'):
                        # If the text is empty but it's a link, try to get the href
                        href = phone_elem.get_attribute('href')
                        if href and 'tel:' in href:
                            phone_text = href.replace('tel:', '')
                    
                    if phone_text:
                        # Clean up the phone number - extract only digits, parentheses, dashes, etc.
                        phone_match = re.search(r'[\d\(\)\-\+\.]+', phone_text)
                        if phone_match:
                            # Remove trailing commas or other punctuation
                            data['AGENT_PHONE'] = phone_match.group(0).rstrip(',.')
                            logging.info(f"Found agent phone: {data['AGENT_PHONE']}")
                            break
                except Exception:
                    continue
                    
            # Create Google Maps URL
            if data['ADDRESS']:
                maps_url = f"https://www.google.com/maps/search/?api=1&query={data['ADDRESS'].replace(' ', '+')}"
                data['MAPS_URL'] = maps_url
                
            # Save data to CSV
            self.save_to_csv(data)
            logging.info(f"Data extracted and saved for listing: {listing_url}")
            
            return data
            
        except Exception as e:
            logging.error(f"Error extracting data from listing: {str(e)}")
            return {}
            
    def save_to_csv(self, data):
        """Save the extracted data to CSV file"""
        try:
            with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writerow(data)
                logging.info(f"Data saved to {self.output_file}")
        except Exception as e:
            logging.error(f"Error saving data to CSV: {str(e)}")
    
    def close(self):
        """Close the browser and clean up resources"""
        if hasattr(self, 'driver'):
            logging.info("Closing browser session")
            try:
                self.driver.quit()
                logging.info("Browser session closed successfully")
            except Exception as e:
                logging.error(f"Error closing browser: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Zillow Property Scraper')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries per zipcode')
    parser.add_argument('--max-listings', type=int, default=0, help='Maximum number of listings to process per zipcode (0 for all listings)')
    args = parser.parse_args()
    
    # Chrome options
    options = uc.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--start-maximized')
    
    # Create the scraper instance with our options
    bot = ZillowScraper(options, args.max_listings)
    
    try:
        
        for zipcode in ZIPCODES:
            logging.info(f"Processing zipcode: {zipcode}")
            retry_count = 0
            success = False
            
            while retry_count < args.max_retries and not success:
                try:
                    bot.search_zipcode(zipcode)
                    success = True
                        
                except Exception as e:
                    retry_count += 1
                    logging.error(f"Error processing zipcode {zipcode} (attempt {retry_count}/{args.max_retries}): {str(e)}")
                    if retry_count < args.max_retries:
                        logging.info(f"Retrying zipcode {zipcode} in 10 seconds...")
                        time.sleep(10)
                    else:
                        logging.error(f"Failed to process zipcode {zipcode} after {args.max_retries} attempts")
            
            # Continue to the next zipcode
            
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
