import time
import random
import os
import csv
import re
import json
import pandas as pd
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
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
log_filename = 'scrape_report.log'

# Create a visible separator between runs
with open(log_filename, 'a', encoding='utf-8') as f:
    separator = "\n" + "="*80 + "\n"
    separator += f" NEW SCRAPING SESSION STARTED AT {time.strftime('%Y-%m-%d %H:%M:%S')} "
    separator += "\n" + "="*80 + "\n"
    f.write(separator)

logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Also log to console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

ZIPCODES = [
    '33009'  # Only processing one zipcode for testing
]

class ZillowScraper:
    def __init__(self, options=None, max_listings=0, keep_browser_open=False, first_page_only=False, debug_all_li=False):
        # Add session start information
        logging.info("-" * 60)
        logging.info("Initializing ZillowScraper...")
        logging.info(f"Session started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Create timestamp for the output file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.output_file = 'zillow_results.csv'
        logging.info(f"Output will be saved to: {self.output_file}")
        
        # Debug options
        self.debug_all_li = debug_all_li
        if debug_all_li:
            logging.info("DEBUG MODE: Will process all li elements as potential listings")
        
        # Track the current zipcode
        self.current_zipcode = None

        # Initialize the CSV file with headers
        self.fieldnames = [
            'ZIPCODE', 'MLS', 'PRICE', 'ADDRESS', 'BEDS', 'BATHS', 'SQFT',
            'URL', 'MAPS_URL', 'DAYS_ON_MARKET', 'AGENT_NAME', 'AGENT_PHONE', 'EMAIL'
        ]

        # Always overwrite and create the CSV file with headers
        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()

        # Initialize Chrome with version matching using undetected_chromedriver
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
            logging.info("Attempting to initialize Chrome with undetected_chromedriver...")
            
            # Try different browser versions if needed
            browser_versions_to_try = [None, 119, 120, 118, 121]
            
            # First attempt - use version 139 (matching your installed Chrome)
            try:
                logging.info("Trying with exact Chrome version 139")
                self.driver = uc.Chrome(
                    options=options,
                    version_main=139,  # Explicitly set to match your Chrome version
                    use_subprocess=True,
                    driver_executable_path=None  # Let it download the correct driver
                )
                logging.info("Successfully initialized Chrome with version 139")
            except Exception as e1:
                logging.warning(f"First attempt with version 139 failed: {str(e1)}")
                
                # Second attempt - try with a clean options object (reusing options causes errors)
                try:
                    logging.info("Trying with clean options object")
                    clean_options = uc.ChromeOptions()
                    # Copy essential arguments
                    clean_options.add_argument("--no-sandbox")
                    clean_options.add_argument("--disable-dev-shm-usage")
                    
                    # Try with version 139
                    self.driver = uc.Chrome(
                        options=clean_options,
                        version_main=139,
                        use_subprocess=True,
                        driver_executable_path=None
                    )
                    logging.info("Successfully initialized Chrome with clean options")
                except Exception as e2:
                    logging.warning(f"Second attempt failed: {str(e2)}")
                    
                    # Third attempt - try to get exact driver version for 139
                    try:
                        logging.info("Trying with specific ChromeDriver version for Chrome 139")
                        # Create a driver_version.py file to override the version detection
                        driver_version_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "driver_version.py")
                        with open(driver_version_path, "w") as f:
                            f.write("version_main = 139\n")
                            f.write("version_full = '139.0.7258.155'\n")
                        
                        # Use a completely fresh options object
                        fresh_options = uc.ChromeOptions()
                        fresh_options.add_argument("--no-sandbox")
                        
                        self.driver = uc.Chrome(
                            options=fresh_options,
                            use_subprocess=True,
                            version_main=139,
                            force_version=True
                        )
                        logging.info("Successfully initialized Chrome with forced version")
                    except Exception as e3:
                        logging.warning(f"Third attempt failed: {str(e3)}")
                        
                        # Final attempt - use standard selenium with undetected options
                        try:
                            logging.info("Trying with standard Selenium as last resort")
                            from selenium import webdriver
                            from selenium.webdriver.chrome.service import Service
                            
                            # Create standard options
                            std_options = webdriver.ChromeOptions()
                            std_options.add_argument("--no-sandbox")
                            std_options.add_argument("--disable-dev-shm-usage")
                            std_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                            std_options.add_experimental_option("useAutomationExtension", False)
                            
                            # Try to initialize with standard selenium
                            self.driver = webdriver.Chrome(options=std_options)
                            
                            # Apply stealth settings after initialization
                            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.7258.155 Safari/537.36'
                            })
                            
                            # Try to execute stealth script
                            try:
                                self.driver.execute_script("""
                                    Object.defineProperty(navigator, 'webdriver', {
                                        get: () => undefined
                                    });
                                """)
                            except:
                                pass
                                
                            logging.info("Successfully initialized with standard Selenium")
                        except Exception as e4:
                            logging.error(f"All initialization attempts failed: {str(e4)}")
                            raise  # Re-raise the exception to stop execution
        except Exception as e:
            logging.error(f"Failed to initialize Chrome: {str(e)}")
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
        self.processed_urls = set()  # Keep track of processed URLs across all pages
        self.keep_browser_open = keep_browser_open  # Flag to determine whether to close the browser
        self.first_page_only = first_page_only  # Flag to only process the first page
        logging.info(f"ZillowScraper initialized successfully. Max listings per zipcode: {max_listings if max_listings > 0 else 'No limit'}")
        if self.keep_browser_open:
            logging.info("Browser will remain open when script finishes")
        if self.first_page_only:
            logging.info("TESTING MODE: Only processing listings from the first page")

    def apply_filters(self):
        """Apply filters for price and beds on the search results page"""
        logging.info("Applying filters to search results")
        
        # First check the current page title - if we're on an "Access denied" page,
        # try to handle the press and hold challenge
        if "Access to this page has been denied" in self.driver.title:
            logging.warning("Detected access denied page before applying filters")
            if not self.handle_press_and_hold_challenge():
                logging.error("Unable to pass bot detection before applying filters - will try to continue anyway")
        else:
            logging.info("No access denied page detected, proceeding with filters")
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
            
            # Wait for page to load
            time.sleep(5)  # Initial wait time
            
            # Check for bot detection "Press & Hold" challenge
            if not self.handle_press_and_hold_challenge():
                # After the handle_press_and_hold_challenge function completes (which now includes
                # checking title after refresh), check if we're still seeing the Access Denied page
                current_title = self.driver.title
                if "Access to this page has been denied" not in current_title:
                    logging.info("Challenge appears to be solved despite reported failure - continuing")
                else:
                    # Try one more time with a different approach - use an alternate URL
                    logging.warning("Still seeing Access Denied - trying with alternate URL format")
                    
                    try:
                        alternate_url = f"https://www.zillow.com/homes/for_sale/{zipcode}/"
                        logging.info(f"Trying alternate URL format: {alternate_url}")
                        self.driver.get(alternate_url)
                        time.sleep(5)
                        
                        # Check if this new URL load bypassed the challenge
                        if "Access to this page has been denied" not in self.driver.title:
                            logging.info("Successfully bypassed challenge with alternate URL")
                        else:
                            # Try the challenge again on the new URL
                            if not self.handle_press_and_hold_challenge():
                                logging.error("Failed to pass bot detection challenge after all attempts - cannot continue")
                                return
                    except Exception as e:
                        logging.warning(f"Failed to load alternate URL: {str(e)} - cannot continue")
                        return
            
            logging.info("Successfully passed any bot detection challenges")
            
        except Exception as e:
            logging.error(f"Error loading URL {url}: {str(e)}")
            return
            
        time.sleep(3)  # Additional wait time before applying filters
        
        # Apply filters
        logging.info("Applying filters to search results")
        self.apply_filters()
        
        # Sort listings by newest first
        logging.info("Sorting listings by newest first")
        self.sort_by_newest()
        
        # Skip counting listings and proceed directly to inspection
        logging.info("Skipping counting and proceeding directly to listing inspection")
        
        # Track total processed listings
        total_processed = 0
        page_num = 1
        has_more_pages = True
        
        # Process all pages until we hit the maximum or run out of pages
        while has_more_pages:
            logging.info(f"Processing page {page_num} of search results")
            
            # If we have a maximum number of listings to process, calculate how many remain
            remaining = self.max_listings - total_processed if self.max_listings > 0 else 0
            
            # Process listings on current page
            # Before processing, let's do a thorough check of what's on the page
            # This is for debugging purposes
            listing_elements = self.driver.find_elements(By.XPATH, '//a[contains(@href, "/homedetails/")]')
            valid_links = []
            duplicate_links = []
            
            for e in listing_elements:
                try:
                    href = e.get_attribute('href')
                    if href and '/homedetails/' in href:
                        if href in self.processed_urls:
                            duplicate_links.append(href)
                        else:
                            valid_links.append(href)
                except:
                    continue
                    
            logging.info(f"DEBUG: Page {page_num} analysis:")
            logging.info(f"  - Total links with '/homedetails/': {len(listing_elements)}")
            logging.info(f"  - New valid links: {len(valid_links)}")
            logging.info(f"  - Already processed links: {len(duplicate_links)}")
            logging.info(f"  - Total listings processed so far: {len(self.processed_urls)}")
            
            processed = self.process_all_listings(remaining if remaining > 0 else 0)
            if processed:
                total_processed += processed
                logging.info(f"Processed {processed} listings on page {page_num}, total so far: {total_processed}")
            
            # If we've hit the maximum, stop
            if self.max_listings > 0 and total_processed >= self.max_listings:
                logging.info(f"Reached maximum number of listings to process ({self.max_listings})")
                break
                
            # Check if we should stop after the first page
            if self.first_page_only:
                logging.info("TESTING MODE: Stopping after first page as requested")
                has_more_pages = False
            else:
                # Try to navigate to the next page
                has_more_pages = self.go_to_next_page()
                if has_more_pages:
                    page_num += 1
                    time.sleep(5)  # Wait between page navigations
                else:
                    logging.info("No more pages to process")
                
        logging.info(f"Finished processing {total_processed} listings across {page_num} page(s)")
        
    def count_listings(self):
        """Count the number of listings in the search results"""
        logging.info("Counting listings in search results")
        wait = WebDriverWait(self.driver, 15)
        
        try:
            # Wait for page to fully load and render all listings
            time.sleep(5)
            
            # Primary selector: grid-search-results container (as specified by user)
            try:
                logging.info("Attempting to find listings using #grid-search-results > ul selector")
                
                # First, check if the container exists
                grid_container = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#grid-search-results > ul"))
                )
                logging.info("Found #grid-search-results > ul container")
                
                # Method 1: Direct CSS selector
                try:
                    listings = self.driver.find_elements(By.CSS_SELECTOR, "#grid-search-results > ul > li")
                    if listings and len(listings) > 0:
                        logging.info(f"Found {len(listings)} listings using direct CSS selector")
                        # Log some details about the first few listings
                        for i in range(min(3, len(listings))):
                            try:
                                listing_id = listings[i].get_attribute("id") or "No ID"
                                listing_class = listings[i].get_attribute("class") or "No class"
                                logging.info(f"Listing {i+1} - ID: {listing_id}, Class: {listing_class}")
                            except Exception as e:
                                logging.debug(f"Error getting details for listing {i+1}: {str(e)}")
                        return len(listings)
                except Exception as e:
                    logging.debug(f"Error with direct CSS selector: {str(e)}")
                
                # Method 2: Nth-child approach (count until we don't find any more)
                try:
                    count = 0
                    for i in range(1, 100):  # Max 100 listings per page
                        try:
                            # Find each nth-child
                            child_selector = f"#grid-search-results > ul > li:nth-child({i})"
                            element = self.driver.find_element(By.CSS_SELECTOR, child_selector)
                            count = i  # If we find this element, update the count
                        except:
                            break  # Stop when we can't find the next child
                    
                    if count > 0:
                        logging.info(f"Found {count} listings using nth-child method")
                        return count
                except Exception as e:
                    logging.debug(f"Error with nth-child approach: {str(e)}")
                
                # Method 3: Get all li elements directly from the container
                try:
                    listings = grid_container.find_elements(By.TAG_NAME, "li")
                    if listings and len(listings) > 0:
                        logging.info(f"Found {len(listings)} listings using container.find_elements")
                        return len(listings)
                except Exception as e:
                    logging.debug(f"Error getting li elements from container: {str(e)}")
                    
            except Exception as e:
                logging.warning(f"Could not find #grid-search-results > ul container: {str(e)}")
            
            # Fallback selectors if the primary one didn't work
            logging.info("Falling back to alternative selectors")
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
                            logging.info(f"Found {count} listings using fallback selector: {selector}")
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
            
        Returns:
            int: Number of listings processed on this page
        """
        if max_listings > 0:
            logging.info(f"Processing up to {max_listings} listings on the page")
        else:
            logging.info("Processing all listings on the page")
            
        wait = WebDriverWait(self.driver, 15)
        # Use the class-level processed_urls to track across pages
        
        # Track processed elements for scrolling
        processed_count = 0
        scroll_batch_size = 5  # Process this many listings before scrolling
        
        try:
            # Store the main window handle for returning after each listing
            main_window = self.driver.current_window_handle
            
            # First, try using the grid-search-results container to find all li elements directly
            try:
                logging.info("Looking for all li elements in #grid-search-results > ul container")
                
                # First, check if the container exists and wait for it
                grid_container = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#grid-search-results > ul"))
                )
                logging.info("Found #grid-search-results > ul container")
                
                # Initial scroll to ensure page content is loaded
                self.driver.execute_script("window.scrollTo(0, 300);")
                time.sleep(1.5)
                
                # We need to handle lazy loading by scrolling and refreshing the list of elements
                # First get an initial set of li elements
                
                # Function to scroll down to load more listings if needed
                def scroll_to_load_more():
                    logging.info("Scrolling down to load more listings...")
                    # Scroll down 75% of the viewport height
                    self.driver.execute_script("window.scrollBy(0, window.innerHeight * 0.75);")
                    time.sleep(1.5)  # Allow time for new content to load
                all_listing_elements = grid_container.find_elements(By.TAG_NAME, "li")
                initial_count = len(all_listing_elements)
                logging.info(f"Initially found {initial_count} li elements")
                
                # For very large pages, we'll scroll progressively and then get a complete list
                total_scrolls = 0
                
                # Adjust scrolling based on how many listings we need
                if max_listings > 0:
                    # If we only need a small number of listings, do fewer scrolls
                    max_scrolls = max(3, min(15, max_listings // 10))  # Scale scrolls based on max_listings
                    logging.info(f"Will scroll up to {max_scrolls} times to find {max_listings} listings")
                else:
                    # Otherwise scroll the maximum number of times
                    max_scrolls = 15
                previous_height = self.driver.execute_script("return document.body.scrollHeight")
                
                while total_scrolls < max_scrolls:
                    # Scroll down by a larger amount to ensure more content loads
                    self.driver.execute_script("window.scrollBy(0, window.innerHeight * 0.9);")
                    total_scrolls += 1
                    logging.info(f"Performed scroll {total_scrolls}/{max_scrolls}")
                    
                    # Wait longer for the page to load content
                    time.sleep(2)
                    
                    # Check if the page height has changed (indicating new content loaded)
                    current_height = self.driver.execute_script("return document.body.scrollHeight")
                    
                    # Check if we have more listings after scrolling
                    current_listings = grid_container.find_elements(By.TAG_NAME, "li")
                    current_count = len(current_listings)
                    
                    if current_count > initial_count:
                        logging.info(f"Scrolling revealed {current_count - initial_count} new listings (now have {current_count} total)")
                        initial_count = current_count
                    
                    if current_height == previous_height:
                        # If no new content after 2 consecutive scrolls, we've likely reached the end
                        if total_scrolls >= 2:
                            logging.info("No new content loaded after scrolling, likely reached the end")
                            break
                    else:
                        previous_height = current_height
                
                # After scrolling, get the updated list of all li elements
                all_listing_elements = grid_container.find_elements(By.TAG_NAME, "li")
                logging.info(f"After scrolling, found {len(all_listing_elements)} li elements (vs initial {initial_count})")
                
                # Skip counting/sampling and go straight to processing each li element
                logging.info("Beginning detailed inspection of each li element")
                
                # Process each li element
                processed_count = 0
                scroll_batch_size = 5  # Scroll after processing this many elements
                
                # Define a function to scroll more while processing if we're near the end
                def scroll_more_if_needed(current_index, total_elements):
                    # If we're 80% through the visible elements, try to scroll for more
                    if current_index > total_elements * 0.8:
                        logging.info(f"Near end of visible listings ({current_index}/{total_elements}), scrolling for more...")
                        # Scroll to reveal more content
                        self.driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8);")
                        time.sleep(2)  # Give time for new content to load
                        
                        # Refresh our list of elements
                        new_elements = grid_container.find_elements(By.TAG_NAME, "li")
                        if len(new_elements) > len(all_listing_elements):
                            logging.info(f"Scrolling revealed {len(new_elements) - len(all_listing_elements)} new listings")
                            return new_elements
                    return all_listing_elements
                
                for i, listing_element in enumerate(all_listing_elements):
                    try:
                        # Stop if we've reached the maximum number of listings to process
                        if max_listings > 0 and processed_count >= max_listings:
                            logging.info(f"Reached maximum number of listings to process ({max_listings})")
                            break
                            
                        # Every 10 elements, check if we need to scroll more to reveal new listings
                        if i > 0 and i % 10 == 0:
                            new_elements = scroll_more_if_needed(i, len(all_listing_elements))
                            if len(new_elements) > len(all_listing_elements):
                                # We found new elements! Update our list and continue with the new elements
                                # Note: This changes our loop behavior, but we'll continue with the current element
                                all_listing_elements = new_elements
                                logging.info(f"Updated listing elements list, now processing {len(all_listing_elements)} elements")
                        
                        # Scroll current element into view if it's part of a new batch
                        # This ensures the element is fully rendered before we try to interact with it
                        if processed_count > 0 and processed_count % scroll_batch_size == 0:
                            try:
                                # Scroll the current element into center view
                                logging.info(f"Scrolling element {i+1} into view (batch {processed_count // scroll_batch_size + 1})")
                                self.driver.execute_script(
                                    "arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});",
                                    listing_element
                                )
                                # Wait briefly for content to load after scrolling
                                time.sleep(1)
                            except Exception as e:
                                logging.warning(f"Error scrolling to element {i+1}: {str(e)}")
                        
                        # Extract element info for debugging
                        try:
                            element_id = listing_element.get_attribute("id") or "No ID"
                            element_class = listing_element.get_attribute("class") or "No class"
                            logging.info(f"Processing li element {i+1}/{len(all_listing_elements)} - ID: {element_id}, Class: {element_class}")
                        except:
                            logging.info(f"Processing li element {i+1}/{len(all_listing_elements)}")
                            
                        # Check if this appears to be a valid property card
                        # Skip this validation if debug-all-li flag is set
                        if not hasattr(self, 'debug_all_li') or not self.debug_all_li:
                            is_valid = self.is_valid_property_card(listing_element)
                            if not is_valid:
                                logging.info(f"Skipping element {i+1} - doesn't appear to be a valid property card")
                                continue
                            else:
                                logging.info(f"Element {i+1} appears to be a valid property card")
                        else:
                            logging.info(f"Processing all li elements in debug mode (element {i+1})")
                        
                        # Find a valid listing URL using multiple strategies
                        listing_url = None
                        
                        # Strategy 1: Look for property-card data attribute and extract link directly
                        try:
                            # Check if this is a real listing by looking for property-card
                            property_card = None
                            
                            # Try multiple selectors to find property card elements
                            for selector in [
                                ".//*[@data-test='property-card']", 
                                ".//article[@role='presentation']",
                                ".//div[contains(@class,'PropertyCard')]",
                                ".//div[contains(@class,'property-card')]"
                            ]:
                                try:
                                    property_card = listing_element.find_element(By.XPATH, selector)
                                    if property_card:
                                        logging.info(f"Found property card in listing {i+1} using selector: {selector}")
                                        break
                                except:
                                    continue
                            
                            if property_card:
                                # First try to find a direct homedetails link
                                homedetails_links = listing_element.find_elements(
                                    By.XPATH, ".//a[contains(@href, '/homedetails/')]"
                                )
                                if homedetails_links:
                                    for link in homedetails_links:
                                        href = link.get_attribute("href")
                                        if href and '/homedetails/' in href:
                                            listing_url = href
                                            logging.info(f"Found homedetails link in listing {i+1}: {listing_url}")
                                            break
                                            
                                # If no direct link, try to extract from schema.org data
                                if not listing_url:
                                    try:
                                        # Look for schema.org JSON data
                                        script_elements = listing_element.find_elements(By.XPATH, ".//script[@type='application/ld+json']")
                                        for script in script_elements:
                                            try:
                                                json_text = script.get_attribute("innerHTML")
                                                json_data = json.loads(json_text)
                                                if 'url' in json_data and '/homedetails/' in json_data['url']:
                                                    listing_url = json_data['url']
                                                    logging.info(f"Extracted URL from JSON data: {listing_url}")
                                                    break
                                            except:
                                                continue
                                    except:
                                        pass
                                        
                                # If still no URL, try to extract ZPID from element
                                if not listing_url:
                                    try:
                                        # Try to extract zpid from element attributes
                                        zpid = None
                                        for attr in ['id', 'data-zpid', 'data-test-id']:
                                            attr_value = property_card.get_attribute(attr)
                                            if attr_value and 'zpid' in attr_value:
                                                zpid_match = re.search(r'(\d+)', attr_value)
                                                if zpid_match:
                                                    zpid = zpid_match.group(1)
                                                    listing_url = f"https://www.zillow.com/homedetails/{zpid}_zpid/"
                                                    logging.info(f"Constructed URL from zpid for listing {i+1}: {listing_url}")
                                                    break
                                    except:
                                        pass
                        except Exception as e:
                            logging.debug(f"Error in strategy 1 for listing {i+1}: {str(e)}")
                        
                        # Strategy 2: Find any link that might be a property link
                        if not listing_url:
                            try:
                                # Look for any links with href
                                all_links = listing_element.find_elements(By.TAG_NAME, "a")
                                for link in all_links:
                                    try:
                                        href = link.get_attribute("href")
                                        if href and '/homedetails/' in href:
                                            listing_url = href
                                            logging.info(f"Found property link in listing {i+1}: {listing_url}")
                                            break
                                    except:
                                        continue
                            except Exception as e:
                                logging.debug(f"Error in strategy 2 for listing {i+1}: {str(e)}")
                        
                        # Skip if we couldn't find a URL
                        if not listing_url:
                            logging.warning(f"Skipping listing {i+1} - No valid URL found")
                            continue
                            
                        # Skip if we've already processed this URL
                        if listing_url in self.processed_urls:
                            logging.info(f"Skipping already processed URL: {listing_url}")
                            continue
                            
                        logging.info(f"Opening listing {i+1} URL: {listing_url}")
                        
                        # Add to processed URLs set
                        self.processed_urls.add(listing_url)
                        
                        # Random wait before opening listing (1-5 seconds)
                        random_wait = random.uniform(1.0, 5.0)
                        logging.info(f"Waiting {random_wait:.2f} seconds before opening listing")
                        time.sleep(random_wait)
                        
                        # Open in a new tab
                        try:
                            # Open new tab with JavaScript
                            self.driver.execute_script(f"window.open('{listing_url}', '_blank');")
                            
                            # Switch to the new tab
                            wait.until(lambda d: len(d.window_handles) > 1)
                            self.driver.switch_to.window(self.driver.window_handles[-1])
                            
                            # Wait for page to load
                            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                            time.sleep(random.uniform(2.0, 3.0))  # Additional wait for elements to load
                            
                            # Extract listing data
                            self.extract_listing_data(listing_url)
                            
                            # Close the tab and switch back to main window
                            self.driver.close()
                            self.driver.switch_to.window(main_window)
                            
                            # Increment processed count
                            processed_count += 1
                            
                            # Add a random delay between listings
                            time.sleep(random.uniform(1.5, 3.0))
                            
                        except Exception as e:
                            logging.error(f"Error processing listing {i+1}: {str(e)}")
                            # Make sure we're back on the main window
                            if main_window in self.driver.window_handles:
                                self.driver.switch_to.window(main_window)
                            
                    except Exception as e:
                        logging.error(f"Error processing listing element {i+1}: {str(e)}")
                        # Make sure we're back on the main window
                        if main_window in self.driver.window_handles:
                            self.driver.switch_to.window(main_window)
                
                logging.info(f"Processed {processed_count} listings from grid container")
                return processed_count
                
            except Exception as e:
                logging.error(f"Error with grid-search-results approach: {str(e)}")
            
            # If the above method failed, fall back to original selectors
            logging.info("Falling back to original selectors")
            listing_selectors = [
                # These selectors find the actual <a> link elements for the listings
                '//ul[contains(@class, "photo-cards")]/li//a[contains(@href, "/homedetails/")]',
                '//div[contains(@id, "search-results")]//li//a[contains(@href, "/homedetails/")]',
                '//div[contains(@class, "search-results")]//li//a[contains(@href, "/homedetails/")]',
                '//div[contains(@class, "result-list")]//li//a[contains(@href, "/homedetails/")]',
                '//ul[contains(@class, "List")]//li//a[contains(@href, "/homedetails/")]',
                '//div[@data-testid="search-result-list"]//li//a[contains(@href, "/homedetails/")]',
                '//main//ul//li[contains(@class, "ListItem")]//a[contains(@href, "/homedetails/")]',
                '//main//div[contains(@class, "StyledPropertyCardDataWrapper")]//a[contains(@href, "/homedetails/")]',
                # Original selectors as fallback
                '//div[contains(@class, "property-card")]/a',
                '//ul[contains(@class, "photo-cards")]//li//a[contains(@class, "property-card")]',
                '//article[contains(@class, "property-card")]//a'
            ]
            
            # Try each selector until we find listings
            all_listings = []
            for selector in listing_selectors:
                try:
                    listings = self.driver.find_elements(By.XPATH, selector)
                    if len(listings) > 0:
                        # Check if these are valid listing links
                        valid_listings = []
                        for listing in listings:
                            try:
                                href = listing.get_attribute('href')
                                if href and '/homedetails/' in href:
                                    valid_listings.append(listing)
                            except:
                                continue
                                
                        # Only use this selector if we found valid listings
                        if len(valid_listings) > 0:
                            all_listings = valid_listings
                            logging.info(f"Found {len(valid_listings)} valid listings with selector: {selector}")
                            break
                except Exception as e:
                    logging.warning(f"Failed to find listings with selector {selector}: {str(e)}")
            
            if not all_listings:
                logging.warning("Could not find any listings with the provided selectors")
                return 0
            
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
                        # Validate it's a proper listing URL
                        if not listing_url:
                            logging.debug(f"Skipping empty URL at position {i+1}")
                            continue
                        elif '/homedetails/' not in listing_url:
                            logging.debug(f"Skipping non-property URL: {listing_url}")
                            continue
                        elif listing_url in self.processed_urls:
                            logging.debug(f"Skipping already processed URL: {listing_url}")
                            continue
                        
                        logging.info(f"Adding new listing URL to processed set: {listing_url}")
                        self.processed_urls.add(listing_url)
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
            
            logging.info(f"Successfully processed {processed_count} listings on this page")
            return processed_count
                
        except Exception as e:
            logging.error(f"Error processing listings: {str(e)}")
            return 0
            
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
                'AGENT_PHONE': '',
                'EMAIL': ''
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
            
            mls_found = False
            for selector in mls_selectors:
                try:
                    mls_elem = self.driver.find_element(By.XPATH, selector)
                    mls_text = mls_elem.text.strip()
                    if mls_text:
                        logging.info(f"Raw MLS text: '{mls_text}'")
                        # Try the standard MLS format
                        mls_match = re.search(r'MLS#?:?\s*([A-Za-z0-9\-]+)', mls_text)
                        if mls_match:
                            data['MLS'] = mls_match.group(1).strip()
                            logging.info(f"Found MLS: {data['MLS']}")
                            mls_found = True
                            break
                except Exception:
                    continue
                    
            # If no MLS was found, use days on market information as MLS
            if not mls_found or not data['MLS']:
                logging.info("No MLS found, trying to use days/hours on market information instead")
                dom_selectors_for_mls = [
                    # Find elements with days/hours information
                    '//dt/strong[contains(text(), "day") or contains(text(), "days") or contains(text(), "hour") or contains(text(), "hours")]',
                    '//dl/dt/strong[contains(text(), "day") or contains(text(), "days") or contains(text(), "hour") or contains(text(), "hours")]',
                    '//span[contains(text(), "day") or contains(text(), "days") or contains(text(), "hour") or contains(text(), "hours")]',
                    '//div[contains(text(), "day") or contains(text(), "days") or contains(text(), "hour") or contains(text(), "hours")]'
                ]
                
                for selector in dom_selectors_for_mls:
                    try:
                        dom_elem = self.driver.find_element(By.XPATH, selector)
                        dom_text = dom_elem.text.strip()
                        if dom_text:
                            logging.info(f"Raw days/hours text for MLS: '{dom_text}'")
                            # Extract the days/hours information for MLS
                            days_match = re.search(r'(\d+)\s*(?:days?|hours?)', dom_text, re.IGNORECASE)
                            if days_match:
                                data['MLS'] = days_match.group(0).strip()  # Include both number and "days"/"hours" text
                                logging.info(f"Using as MLS: {data['MLS']}")
                                break
                    except Exception:
                        continue
                    
            # Extract days on market
            dom_selectors = [
                # Based on the HTML structure with StyledOverviewStats
                '//dl[contains(@class, "StyledOverviewStats")]/dt[1]/strong',
                '//dl[contains(@class, "StyledOverviewStats")]/dt[1]/strong[contains(text(), "day") or contains(text(), "days")]',
                # Additional selectors for newer HTML structure
                '//dl[contains(@class, "kpgmGL")]/dt[1]/strong',
                '//dl/dt[1]/strong[contains(text(), "day") or contains(text(), "days")]',
                # More generic selectors that look for the first strong tag within dt that contains "days"
                '//dt/strong[contains(text(), "day") or contains(text(), "days")]',
                # Previous specific XPath
                '//*[@id="search-detail-lightbox"]/div[1]/div[1]/div[1]/section/div/div[3]/div[1]/div[1]/dl/dt[1]/strong',
                # Additional XPath selectors for the same element with slight variations
                '//section//dl/dt/strong[contains(text(), "day") or contains(text(), "Day")]',
                # Previous selectors as fallbacks
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
                        logging.info(f"Raw days on market text: '{dom_text}'")
                        # Try to extract number followed by "day", "days", "hour", or "hours"
                        dom_match = re.search(r'(\d+\s*(?:days?|hours?))', dom_text, re.IGNORECASE)
                        if dom_match:
                            data['DAYS_ON_MARKET'] = dom_match.group(1)  # Get the full match (number + unit)
                            logging.info(f"Found days/hours on market: {data['DAYS_ON_MARKET']}")
                            break
                        else:
                            # Try to match just days
                            dom_match = re.search(r'(\d+)\s*days?', dom_text, re.IGNORECASE)
                            if dom_match:
                                # Reconstruct with proper formatting
                                data['DAYS_ON_MARKET'] = f"{dom_match.group(1)} days"
                                logging.info(f"Found days on market: {data['DAYS_ON_MARKET']}")
                                break
                            else:
                                # Try to match just hours
                                dom_match = re.search(r'(\d+)\s*hours?', dom_text, re.IGNORECASE)
                                if dom_match:
                                    # Reconstruct with proper formatting
                                    data['DAYS_ON_MARKET'] = f"{dom_match.group(1)} hours"
                                    logging.info(f"Found hours on market: {data['DAYS_ON_MARKET']}")
                                    break
                                else:
                                    # Fall back to just getting any number if the format isn't exactly as expected
                                    dom_match = re.search(r'(\d+)', dom_text)
                                    if dom_match:
                                        # Just use the number and assume days
                                        data['DAYS_ON_MARKET'] = f"{dom_match.group(1)} days"
                                        logging.info(f"Found days on market (fallback method): {data['DAYS_ON_MARKET']}")
                                        break
                except Exception as e:
                    logging.debug(f"Error with DOM selector '{selector}': {str(e)}")
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
            
            # Extract agent email using the specific element
            email_selectors = [
                # Direct email selectors
                '//a[contains(@href, "mailto:")]',
                '//span[contains(text(), "@") and contains(text(), ".")]',
                '//div[contains(text(), "@") and contains(text(), ".")]',
                # Look for contact information sections
                '//div[contains(@class, "contact-info")]//a[contains(@href, "mailto:")]',
                '//div[contains(@class, "agent-info")]//a[contains(@href, "mailto:")]',
                '//span[contains(@class, "email")]',
                '//div[contains(@class, "email")]'
            ]
            
            for selector in email_selectors:
                try:
                    email_elem = self.driver.find_element(By.XPATH, selector)
                    email_text = email_elem.text.strip()
                    
                    # If no text but has href, extract from href
                    if not email_text and 'href' in email_elem.get_attribute('outerHTML'):
                        href = email_elem.get_attribute('href')
                        if href and 'mailto:' in href:
                            email_text = href.replace('mailto:', '')
                    
                    if email_text:
                        # Validate it looks like an email
                        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email_text)
                        if email_match:
                            data['EMAIL'] = email_match.group(0)
                            logging.info(f"Found agent email: {data['EMAIL']}")
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
            
    def go_to_next_page(self):
        """Navigate to the next page of search results if available"""
        logging.info("Attempting to navigate to the next page of results")
        wait = WebDriverWait(self.driver, 10)
        
        # Various selectors for "Next" buttons or pagination elements
        next_page_selectors = [
            '//a[contains(@title, "Next page") or contains(@aria-label, "Next page")]',
            '//a[contains(@class, "next") or contains(@class, "Next")]',
            '//button[contains(@title, "Next") or contains(@aria-label, "Next")]',
            '//button[contains(text(), "Next")]',
            '//a[contains(text(), "Next")]',
            '//li[contains(@class, "next")]/a',
            '//span[contains(@class, "next")]/a',
            '//nav[contains(@class, "pagination")]//a[contains(@class, "next")]',
            '//span[contains(@class, "PaginationButton") and contains(text(), ">")]',
            '//button[@data-testid="pagination-next-btn" or contains(@class, "pagination-next")]',
            # Common arrow icons that might indicate next page
            '//a[contains(@class, "next-page") or contains(@class, "nextPage")]',
            '//button[.//*[local-name()="svg" and contains(@class, "arrow-right")]]',
            '//button[.//*[contains(@class, "icon-right")]]'
        ]
        
        for selector in next_page_selectors:
            try:
                next_button = self.driver.find_element(By.XPATH, selector)
                
                # Check if the button is disabled or not clickable
                if next_button.get_attribute("disabled") == "true" or "disabled" in next_button.get_attribute("class") or not next_button.is_displayed():
                    logging.info("Next page button is disabled or not available - reached the last page")
                    return False
                
                # Scroll into view for better visibility
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                time.sleep(2)
                
                # Try to click
                logging.info(f"Found next page button with selector: {selector}")
                next_button.click()
                
                # Wait for page to load
                time.sleep(5)
                wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
                
                # Additional wait for elements to render
                time.sleep(3)
                
                # Check if we're on an "Access denied" page after navigation
                if "Access to this page has been denied" in self.driver.title:
                    logging.warning("Detected access denied page after navigation")
                    
                    # Try to pass the challenge
                    if self.handle_press_and_hold_challenge():
                        logging.info("Successfully passed challenge after navigation")
                    else:
                        # Check title again after challenge attempts
                        if "Access to this page has been denied" not in self.driver.title:
                            logging.info("Challenge appears to be solved despite reported failure")
                        else:
                            logging.error("Failed to pass bot detection challenge after navigating to next page")
                            # We'll try to continue anyway - might work for some elements
                
                logging.info("Successfully navigated to the next page")
                return True
                
            except Exception as e:
                logging.warning(f"Failed to click next page button with selector {selector}: {str(e)}")
                continue
        
        logging.info("No next page button found - likely reached the last page")
        return False
    
    def go_to_next_page(self):
        """Navigate to the next page of search results
        
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        logging.info("Attempting to navigate to the next page")
        
        try:
            # Wait a bit to ensure the page is fully loaded
            time.sleep(3)
            
            # Try different selectors for the next page button
            next_page_selectors = [
                '//a[@title="Next page"]',
                '//a[contains(@class, "next")]',
                '//button[contains(@aria-label, "Next page")]',
                '//button[contains(text(), "Next")]',
                '//a[contains(text(), "Next")]',
                '//span[contains(text(), "Next")]/parent::*',
                '//button[contains(@class, "PaginationButton") and contains(@aria-label, "Next")]',
                '//li[contains(@class, "PaginationJumpItem")]/following-sibling::li//button'
            ]
            
            for selector in next_page_selectors:
                try:
                    next_button = self.driver.find_element(By.XPATH, selector)
                    if next_button.is_displayed() and next_button.is_enabled():
                        logging.info(f"Found next page button with selector: {selector}")
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                        time.sleep(1)
                        next_button.click()
                        
                        # Wait for the page to load
                        time.sleep(5)
                        logging.info("Navigated to the next page successfully")
                        return True
                except Exception as e:
                    logging.debug(f"Next page selector {selector} failed: {str(e)}")
                    continue
            
            logging.info("No next page button found - likely on the last page")
            return False
            
        except Exception as e:
            logging.error(f"Error navigating to next page: {str(e)}")
            return False
    
    def extract_schema_data(self, element):
        """
        Extract listing data from schema.org JSON-LD in the listing element
        
        Args:
            element: Selenium WebElement containing the listing
            
        Returns:
            dict: Extracted schema.org data or empty dict if none found
        """
        try:
            # Look for schema.org JSON data in script tags
            script_elements = element.find_elements(By.XPATH, ".//script[@type='application/ld+json']")
            if not script_elements:
                return {}
                
            for script in script_elements:
                try:
                    # Get the JSON content
                    json_text = script.get_attribute("innerHTML")
                    if not json_text:
                        continue
                        
                    # Parse the JSON data
                    json_data = json.loads(json_text)
                    
                    # Check if this is property data with expected fields
                    if '@type' not in json_data or 'url' not in json_data:
                        continue
                        
                    if json_data['@type'] not in ['SingleFamilyResidence', 'Apartment', 'House']:
                        continue
                        
                    # Extract relevant fields
                    property_data = {
                        'property_url': json_data.get('url', ''),
                        'address': json_data.get('name', '')
                    }
                    
                    # Extract address details
                    if 'address' in json_data and isinstance(json_data['address'], dict):
                        addr = json_data['address']
                        property_data.update({
                            'street': addr.get('streetAddress', ''),
                            'city': addr.get('addressLocality', ''),
                            'state': addr.get('addressRegion', ''),
                            'zip': addr.get('postalCode', '')
                        })
                    
                    # Extract floor size if available
                    if 'floorSize' in json_data and isinstance(json_data['floorSize'], dict):
                        size_value = json_data['floorSize'].get('value', '')
                        # Remove any commas from the value
                        if isinstance(size_value, str):
                            size_value = size_value.replace(',', '')
                        try:
                            property_data['sqft'] = int(float(size_value))
                        except (ValueError, TypeError):
                            property_data['sqft'] = size_value
                    
                    # Extract bedrooms count
                    if 'numberOfRooms' in json_data:
                        try:
                            property_data['beds'] = int(json_data['numberOfRooms'])
                        except (ValueError, TypeError):
                            property_data['beds'] = json_data['numberOfRooms']
                    
                    # Extract geographic coordinates
                    if 'geo' in json_data and isinstance(json_data['geo'], dict):
                        geo = json_data['geo']
                        property_data.update({
                            'latitude': geo.get('latitude', ''),
                            'longitude': geo.get('longitude', '')
                        })
                    
                    # Validate we have a property URL that contains homedetails
                    if property_data.get('property_url') and '/homedetails/' in property_data['property_url']:
                        logging.info(f"Successfully extracted schema.org data: {property_data}")
                        return property_data
                
                except Exception as e:
                    logging.debug(f"Error parsing schema.org data: {str(e)}")
                    continue
                    
            return {}
            
        except Exception as e:
            logging.debug(f"Error extracting schema.org data: {str(e)}")
            return {}
    
    def handle_press_and_hold_challenge(self, max_attempts=3):
        """Handle the 'Press & Hold' bot detection challenge
        
        Args:
            max_attempts: Maximum number of attempts to pass the challenge
            
        Returns:
            bool: True if challenge was passed or not detected, False otherwise
        """
        try:
            # Check if we're facing a bot detection page
            page_title = self.driver.title
            page_source = self.driver.page_source
            logging.info(f"Current page title: {page_title}")
            
            # Check for bot detection indicators
            bot_detection_indicators = [
                "Access to this page has been denied",
                "Press & Hold",
                "press and hold",
                "security check",
                "bot detection",
                "human verification"
            ]
            
            is_bot_detection = False
            for indicator in bot_detection_indicators:
                if indicator.lower() in page_title.lower() or indicator.lower() in page_source.lower():
                    is_bot_detection = True
                    logging.info(f"Bot detection identified by indicator: {indicator}")
                    break
                    
            if is_bot_detection:
                logging.info("Detected bot protection challenge with 'Press & Hold' button")
                
                # Look for the Press & Hold button using different selectors
                press_hold_selectors = [
                    "//p[contains(text(), 'Press') and contains(text(), 'Hold')]",
                    "//p[@id='RvMKxvJTAzNJLSy' and @class='QIFoYgojXGVhqnd']",
                    "//*[contains(text(), 'Press') and contains(text(), 'Hold')]",
                    "//button[contains(text(), 'Press')]",
                    "//div[contains(@class, 'challenge')]//p",
                    "//div[contains(@class, 'captcha')]//p",
                    "//p[contains(@class, 'QIFoYgojXGVhqnd')]"  # Class from your example
                ]
                
                attempts = 0
                while attempts < max_attempts:
                    attempts += 1
                    logging.info(f"Attempt {attempts}/{max_attempts} to solve Press & Hold challenge")
                    
                    # Try each selector
                    button = None
                    for selector in press_hold_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                text = element.text.lower()
                                if 'press' in text and ('&' in text or 'and' in text or 'hold' in text):
                                    button = element
                                    logging.info(f"Found 'Press & Hold' button: '{element.text}' using selector: {selector}")
                                    break
                            if button:
                                break
                        except:
                            continue
                    
                    if not button:
                        # Try a more aggressive approach - look for any clickable elements
                        try:
                            logging.info("No specific 'Press & Hold' button found, looking for any clickable elements")
                            all_elements = self.driver.find_elements(By.XPATH, "//button | //p | //div[@role='button']")
                            for element in all_elements:
                                try:
                                    if element.is_displayed() and element.is_enabled():
                                        text = element.text.lower()
                                        if text and len(text) < 30:  # Likely to be a button text
                                            logging.info(f"Found potential interactive element: '{element.text}'")
                                            button = element
                                            break
                                except:
                                    continue
                        except:
                            pass
                    
                    if button:
                        try:
                            logging.info(f"Attempting to press and hold button: '{button.text}'")
                            
                            # First scroll into view
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", button)
                            time.sleep(1)
                            
                            # Create action chain for press and hold
                            actions = ActionChains(self.driver)
                            
                            # Try with longer press times on subsequent attempts
                            hold_time = 3 + (attempts * 2)  # Increase hold time with each attempt
                            
                            # Move to the button first
                            actions.move_to_element(button)
                            actions.pause(0.5)
                            
                            # Try different strategies based on attempt number
                            if attempts == 1:
                                # First attempt: normal click and hold
                                actions.click_and_hold()
                                actions.pause(hold_time)  # Hold for specified time
                                actions.release()
                                actions.perform()
                            else:
                                # Subsequent attempts: try a more human-like interaction
                                # First click normally, then click and hold
                                actions.click()
                                actions.pause(0.5)
                                actions.click_and_hold()
                                
                                # Add a slight mouse movement during holding to simulate human behavior
                                for i in range(3):
                                    actions.move_by_offset(1, 0)
                                    actions.pause(0.1)
                                    actions.move_by_offset(-1, 0)
                                    actions.pause(0.1)
                                
                                actions.pause(hold_time)
                                actions.release()
                                actions.perform()
                            
                            logging.info(f"Completed press and hold for {hold_time} seconds")
                            
                            # Wait for the page to load after passing the challenge
                            time.sleep(5)
                            
                            # Check if we passed the challenge
                            new_page_title = self.driver.title
                            logging.info(f"Page title after attempt {attempts}: {new_page_title}")
                            
                            if "Access to this page has been denied" not in new_page_title and "Press & Hold" not in self.driver.page_source:
                                logging.info(f"Successfully passed the challenge on attempt {attempts}")
                                return True
                            else:
                                logging.warning(f"Challenge still active after attempt {attempts}")
                        except Exception as e:
                            logging.error(f"Error during press and hold attempt {attempts}: {str(e)}")
                    else:
                        logging.warning(f"Could not find any 'Press & Hold' button on attempt {attempts}")
                        
                    # If we reach here, the attempt failed - refresh the page and try again
                    if attempts < max_attempts:
                        logging.info("Refreshing page before next attempt")
                        try:
                            self.driver.refresh()
                            time.sleep(5)  # Give page time to fully load after refresh
                            
                            # Check if the title has changed after refresh - maybe challenge was solved
                            refreshed_title = self.driver.title
                            logging.info(f"Page title after refresh: {refreshed_title}")
                            
                            # If the "Access denied" title is gone after refresh, we've passed the challenge
                            if "Access to this page has been denied" not in refreshed_title:
                                logging.info("Challenge appears to be solved after page refresh!")
                                return True
                                
                        except Exception as e:
                            logging.error(f"Error refreshing page: {str(e)}")
                            time.sleep(3)  # Still wait even if refresh fails
                
                logging.error(f"Failed to pass 'Press & Hold' challenge after {max_attempts} attempts")
                return False
            else:
                logging.info("No bot protection challenge detected")
                return True
                
        except Exception as e:
            logging.error(f"Error handling press and hold challenge: {str(e)}")
            return False
    
    def is_valid_property_card(self, element):
        """
        Check if a li element is a valid property card listing
        
        Args:
            element: Selenium WebElement to check
            
        Returns:
            bool: True if the element appears to be a valid property card
        """
        try:
            # First check: Any <li> element that has an <article> element is a valid listing
            try:
                article_elements = element.find_elements(By.TAG_NAME, "article")
                if article_elements:
                    logging.debug("Valid listing identified by presence of article element")
                    return True
            except:
                pass
                
            # Analyze the class attributes next - reliable indicator
            try:
                class_name = element.get_attribute("class") or ""
                # Based on your examples, all valid listings have both these classes
                if "ListItem-c11n-8-109-3__sc-13rwu5a-0" in class_name and "StyledListCardWrapper-srp-8-109-3__sc-r47yyl-0" in class_name:
                    logging.debug("Valid listing identified by ListItem and StyledListCardWrapper classes")
                    return True
            except:
                pass
                
            # Check for script with ld+json (schema.org data) - Very strong indicator
            # All example listings had this element with property data
            try:
                schema_scripts = element.find_elements(By.XPATH, ".//script[@type='application/ld+json']")
                if schema_scripts:
                    for script in schema_scripts:
                        try:
                            json_text = script.get_attribute("innerHTML")
                            if json_text and ('homedetails' in json_text or 'SingleFamilyResidence' in json_text):
                                logging.debug("Valid listing identified by schema.org data")
                                return True
                        except:
                            pass
            except:
                pass
                
            # Check for article with data-test="property-card" - Very reliable
            # All example listings had this element
            try:
                property_articles = element.find_elements(By.XPATH, ".//article[@data-test='property-card']")
                if property_articles:
                    logging.debug("Valid listing identified by article with data-test=property-card")
                    return True
            except:
                pass
                
            # Check for presence of address element - All listings had this
            try:
                address_elements = element.find_elements(By.TAG_NAME, "address")
                if address_elements:
                    logging.debug("Valid listing identified by address element")
                    return True
            except:
                pass
                
            # Check for price element
            try:
                price_elements = element.find_elements(
                    By.XPATH, ".//*[@data-test='property-card-price']"
                )
                if price_elements:
                    logging.debug("Valid listing identified by property-card-price element")
                    return True
            except:
                pass
                
            # Check for homedetails URL in any link
            try:
                links = element.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute("href")
                    if href and '/homedetails/' in href:
                        logging.debug("Valid listing identified by homedetails URL")
                        return True
            except:
                pass
                
            # Check for property-card-data class which contains listing details
            try:
                data_wrappers = element.find_elements(
                    By.XPATH, ".//*[contains(@class, 'property-card-data')]"
                )
                if data_wrappers:
                    logging.debug("Valid listing identified by property-card-data class")
                    return True
            except:
                pass
                
            # Look for bed/bath/sqft indicators - All valid listings had these
            try:
                details_list = element.find_elements(
                    By.XPATH, ".//ul[contains(@class, 'StyledPropertyCardHomeDetailsList')]"
                )
                if details_list:
                    logging.debug("Valid listing identified by StyledPropertyCardHomeDetailsList")
                    return True
            except:
                pass
                
            # Check for zpid in any element (very specific to property listings)
            try:
                elements_with_zpid = element.find_elements(By.XPATH, ".//*[contains(@id, 'zpid_')]")
                if elements_with_zpid:
                    logging.debug("Valid listing identified by zpid element")
                    return True
            except:
                pass
                
            # Last resort: Check for combination of indicators in HTML
            try:
                html = element.get_attribute("outerHTML") or ""
                # Core indicators that must be present for valid listings
                required_indicators = ['homedetails', 'zpid']
                # Secondary indicators where at least a few should be present
                secondary_indicators = ['property-card', 'address', 'price', 'bds', 'ba', 'sqft', 'StyledPropertyCard']
                
                # Check for required indicators (must have at least one)
                required_hits = sum(1 for indicator in required_indicators if indicator in html.lower())
                secondary_hits = sum(1 for indicator in secondary_indicators if indicator in html.lower())
                
                if required_hits > 0 and secondary_hits >= 3:
                    logging.debug(f"Valid listing identified by HTML indicators (required: {required_hits}, secondary: {secondary_hits})")
                    return True
            except:
                pass
                
            # If we got here, it's probably not a valid listing
            logging.debug("Element not identified as a valid listing")
            return False
            
        except Exception as e:
            logging.debug(f"Error checking if element is a property card: {str(e)}")
            return False
    
    def close(self):
        """Close the browser and clean up resources"""
        if hasattr(self, 'driver'):
            if self.keep_browser_open:
                logging.info("Keeping browser session open as requested")
            else:
                logging.info("Closing browser session")
                try:
                    self.driver.quit()
                    logging.info("Browser session closed successfully")
                except Exception as e:
                    logging.error(f"Error closing browser: {str(e)}")
        
        # Add session end information
        logging.info(f"Session ended at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info("-" * 60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Zillow Property Scraper')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries per zipcode')
    parser.add_argument('--max-listings', type=int, default=0, help='Maximum number of listings to process per zipcode (0 for all listings)')  # Changed to 10 for testing
    parser.add_argument('--keep-browser-open', action='store_true', help='Keep browser open when the script finishes')
    parser.add_argument('--first-page-only', action='store_true', help='Only process listings from the first page (for testing)')
    parser.add_argument('--zipcode', type=str, help='Specific zipcode to process (overrides the default list)')
    parser.add_argument('--debug-all-li', action='store_true', help='Debug mode: process all li elements as potential listings')
    parser.add_argument('--headless', action='store_true', help='Run Chrome in headless mode (without visible browser)')
    args = parser.parse_args()
    
    # Chrome options for undetected_chromedriver
    options = uc.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--start-maximized')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Add headless mode if requested
    if args.headless:
        logging.info("Running in headless mode")
        options.add_argument('--headless')  # For undetected_chromedriver
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Add additional options to make headless mode more stable
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-software-rasterizer')
        
        # Add a mainstream user agent to help avoid detection
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.7258.155 Safari/537.36')
    
    # Create the scraper instance with our options
    bot = ZillowScraper(options, args.max_listings, args.keep_browser_open, args.first_page_only, args.debug_all_li)
    
    try:
        # Use the zipcode from command line if provided, otherwise use the predefined list
        zipcode_list = [args.zipcode] if args.zipcode else ZIPCODES
        
        for zipcode in zipcode_list:
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
            delay = random.uniform(2.0, 5.0)
            logging.info(f"Waiting {delay:.1f} seconds before next zipcode...")
            time.sleep(delay)

    except KeyboardInterrupt:
        logging.info("Scraper stopped by user")
        logging.info("Summary: Script execution was interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        logging.error("Summary: Script execution failed due to unexpected error")
    else:
        logging.info("Summary: Script execution completed successfully")
        
        # New logic: search for agents on Nestfully after scraping listings
        try:
            logging.info("Starting Nestfully agent search...")
            
            # Read the CSV file
            csv_file = bot.output_file
            agent_data = []
            
            if os.path.exists(csv_file):
                with open(csv_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['AGENT_NAME']:  # Only add entries with agent names
                            agent_data.append(row)
            
            if agent_data:
                logging.info(f"Found {len(agent_data)} agents in CSV to search on Nestfully")
                
                # Verify we have a valid browser before proceeding
                if not bot.driver:
                    logging.error("No valid browser available for Nestfully search")
                    raise Exception("No valid browser available")
                
                # Continue using the existing browser instance - don't create a new one
                # This avoids ChromeDriver version compatibility issues
                logging.info("Using existing browser instance for Nestfully agent searches")
                
                # Process each agent
                for index, agent_row in enumerate(agent_data):
                    try:
                        agent_name = agent_row['AGENT_NAME'].strip()
                        if not agent_name:
                            continue
                            
                        # Split into first and last name
                        name_parts = agent_name.split()
                        if len(name_parts) >= 2:
                            # Create a list of name combinations to try
                            name_combinations = []
                            
                            # Combination 1: Default - first word as first name, last word as last name
                            name_combinations.append({
                                'first_name': name_parts[0],
                                'last_name': name_parts[-1]
                            })
                            
                            # For names with 3 parts, try various combinations
                            if len(name_parts) == 3:
                                # Combination 2: first name = first part, last name = all remaining parts
                                name_combinations.append({
                                    'first_name': name_parts[0],
                                    'last_name': ' '.join(name_parts[1:])
                                })
                                
                                # Combination 3: first name = first two parts, last name = remaining parts
                                name_combinations.append({
                                    'first_name': ' '.join(name_parts[:2]),
                                    'last_name': ' '.join(name_parts[2:])
                                })
                            
                            # For names with 4+ parts, add more combinations
                            elif len(name_parts) >= 4:
                                    # Clear existing combinations to match exactly what was requested
                                    name_combinations = []
                                    
                                    # Combination 1: First word as first name, last word as last name
                                    # Ex: Mark Damien Dagar Cosadio -> First: Mark, Last: Cosadio
                                    name_combinations.append({
                                        'first_name': name_parts[0],
                                        'last_name': name_parts[-1]
                                    })
                                    
                                    # Combination 2: First two words as first name, last word as last name
                                    # Ex: Mark Damien Dagar Cosadio -> First: Mark Damien, Last: Cosadio
                                    name_combinations.append({
                                        'first_name': ' '.join(name_parts[:2]),
                                        'last_name': name_parts[-1]
                                    })
                                    
                                    # Combination 3: First two words as first name, last two words as last name
                                    # Ex: Mark Damien Dagar Cosadio -> First: Mark Damien, Last: Dagar Cosadio
                                    name_combinations.append({
                                        'first_name': ' '.join(name_parts[:2]),
                                        'last_name': ' '.join(name_parts[2:])
                                    })
                                    
                                    # Combination 4: First three words as first name, last word as last name
                                    # Ex: Mark Damien Dagar Cosadio -> First: Mark Damien Dagar, Last: Cosadio
                                    name_combinations.append({
                                        'first_name': ' '.join(name_parts[:3]),
                                        'last_name': name_parts[-1]
                                    })
                                    
                                    # Combination 5: First word as first name, remaining words as last name
                                    # Ex: Mark Damien Dagar Cosadio -> First: Mark, Last: Damien Dagar Cosadio
                                    name_combinations.append({
                                        'first_name': name_parts[0],
                                        'last_name': ' '.join(name_parts[1:])
                                    })
                            
                            logging.info(f"Will try {len(name_combinations)} name combinations for agent: {agent_name} ({index+1}/{len(agent_data)})")
                            
                            # Set initial combination
                            first_name = name_parts[0]
                            last_name = name_parts[-1]
                            
                            # Track if we found the agent with any combination
                            agent_found = False
                            agent_email = None
                            
                            # Try each name combination
                            for combo_idx, combo in enumerate(name_combinations):
                                if agent_found:
                                    break
                                    
                                first_name = combo['first_name']
                                last_name = combo['last_name']
                                
                                logging.info(f"Trying name combination {combo_idx+1}: '{first_name}' '{last_name}'")
                            
                                # Navigate directly to Nestfully agent search page for each attempt
                                bot.driver.get("https://www.nestfully.com/agentsearch/search.aspx")
                                time.sleep(random.uniform(1.0, 3.0))
                                
                                # Wait for the page to load
                                wait = WebDriverWait(bot.driver, 10)
                                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                            
                                # For each name combination, find and fill form fields
                                try:
                                    # Try different possible input field selectors
                                    first_name_selectors = [
                                        (By.ID, "Master_FirstName"),
                                        (By.XPATH, "//input[@placeholder='First Name...']"),
                                        (By.XPATH, "//input[contains(@name, 'FirstName')]"),
                                        (By.XPATH, "//input[contains(@id, 'FirstName')]"),
                                        (By.XPATH, "//label[contains(text(), 'First')]/following-sibling::input"),
                                        (By.XPATH, "//label[contains(text(), 'First')]/..//input")
                                    ]
                                    
                                    first_name_field = None
                                    for selector in first_name_selectors:
                                        try:
                                            first_name_field = wait.until(EC.presence_of_element_located(selector))
                                            if first_name_field and first_name_field.is_displayed():
                                                logging.info(f"Found first name input with selector: {selector}")
                                                break
                                        except:
                                            continue
                                            
                                    if not first_name_field:
                                        raise Exception("Could not find first name input field")
                                    
                                    first_name_field.clear()
                                    first_name_field.send_keys(first_name)
                                    logging.info(f"Entered first name: {first_name}")
                                    
                                    # Find and fill last name field - try multiple selectors
                                    last_name_selectors = [
                                        (By.ID, "Master_LastName"),
                                        (By.XPATH, "//input[@placeholder='Last Name...']"),
                                        (By.XPATH, "//input[contains(@name, 'LastName')]"),
                                        (By.XPATH, "//input[contains(@id, 'LastName')]"),
                                        (By.XPATH, "//label[contains(text(), 'Last')]/following-sibling::input"),
                                        (By.XPATH, "//label[contains(text(), 'Last')]/..//input")
                                    ]
                                    
                                    last_name_field = None
                                    for selector in last_name_selectors:
                                        try:
                                            last_name_field = bot.driver.find_element(*selector)
                                            if last_name_field and last_name_field.is_displayed():
                                                logging.info(f"Found last name input with selector: {selector}")
                                                break
                                        except:
                                            continue
                                    
                                    if not last_name_field:
                                        raise Exception("Could not find last name input field")
                                        
                                    last_name_field.clear()
                                    last_name_field.send_keys(last_name)
                                    logging.info(f"Entered last name: {last_name}")
                                    
                                        # Send Enter key to submit the form instead of clicking a button
                                    last_name_field.send_keys(Keys.RETURN)
                                    logging.info(f"Pressed Enter key to submit the search for combination {combo_idx+1}")
                                
                                except Exception as e:
                                    logging.error(f"Error filling form with combination {combo_idx+1}: {str(e)}")
                                    continue
                                
                                # Wait for results to load
                                time.sleep(random.uniform(1.0, 3.0))
                                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                                
                                try:
                                    # Try different selectors to find the agent link
                                    agent_link_selectors = [
                                        f"//a[contains(text(), '{first_name}') and contains(text(), '{last_name}')]",
                                        f"//a[contains(text(), '{agent_name}')]",
                                        f"//a[contains(@class, 'detail-page') and contains(text(), '{last_name}')]",
                                        f"//a[contains(@href, '{first_name}{last_name}') or contains(@href, '{first_name}-{last_name}')]",
                                        "//a[contains(@class, 'ao_results_icon_text')]",
                                        "//a[contains(@class, 'detail-page')]"
                                    ]
                                    
                                    for selector in agent_link_selectors:
                                        try:
                                            agent_links = bot.driver.find_elements(By.XPATH, selector)
                                            if agent_links:
                                                for link in agent_links:
                                                    if link.is_displayed() and (first_name.lower() in link.text.lower() or last_name.lower() in link.text.lower()):
                                                        logging.info(f"Found agent link with combination {combo_idx+1}: {link.text}")
                                                        link.click()
                                                        found_agent_link = True
                                                        agent_found = True  # Set the flag to stop trying other combinations
                                                        
                                                        # Wait for detail page to load
                                                        time.sleep(random.uniform(1.0, 3.0))
                                                        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                                                        
                                                        # Try to extract email address
                                                        email_selectors = [
                                                            "//a[@id='hlAgentEmailAddress']",
                                                            "//a[contains(@href, 'AgentEmailAddress')]",
                                                            "//a[contains(@href, 'mailto:')]",
                                                            "//a[contains(text(), '@') and contains(text(), '.com')]",
                                                            "//span[contains(text(), '@') and contains(text(), '.com')]",
                                                            "//div[contains(text(), '@') and contains(text(), '.com')]"
                                                        ]
                                                        
                                                        for email_selector in email_selectors:
                                                            try:
                                                                email_elements = bot.driver.find_elements(By.XPATH, email_selector)
                                                                for email_elem in email_elements:
                                                                    if '@' in email_elem.text and '.' in email_elem.text:
                                                                        agent_email = email_elem.text.strip()
                                                                        logging.info(f"Found email address using combination {combo_idx+1}: {agent_email}")
                                                                        break
                                                                    elif 'href' in email_elem.get_attribute('outerHTML'):
                                                                        href = email_elem.get_attribute('href')
                                                                        if 'AgentEmailAddress=' in href:
                                                                            # Extract email from href parameter
                                                                            email_match = re.search(r'AgentEmailAddress=([^&]+)', href)
                                                                            if email_match:
                                                                                agent_email = email_match.group(1)
                                                                                logging.info(f"Extracted email from href using combination {combo_idx+1}: {agent_email}")
                                                                                break
                                                                
                                                                if agent_email:
                                                                    break
                                                            except:
                                                                continue
                                                        
                                                        break
                                                
                                                if found_agent_link:
                                                    break
                                        except:
                                            continue
                                    
                                    # If we found an email, we'll break out of the combinations loop
                                    if agent_email:
                                        logging.info(f"Successfully found email with combination {combo_idx+1}")
                                except Exception as e:
                                    logging.error(f"Error finding agent link or email with combination {combo_idx+1}: {str(e)}")
                            
                            # After trying all combinations, if we found an email, update the CSV
                            if agent_email:
                                # Read the current CSV file
                                rows = []
                                try:
                                    with open(csv_file, 'r', newline='', encoding='utf-8') as f:
                                        reader = csv.DictReader(f)
                                        for row in reader:
                                            # Update the email for the matching agent
                                            if row['AGENT_NAME'].strip() == agent_name.strip():
                                                row['EMAIL'] = agent_email
                                            rows.append(row)
                                    
                                    # Write the updated data back to the CSV file
                                    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                                        writer = csv.DictWriter(f, fieldnames=reader.fieldnames)
                                        writer.writeheader()
                                        writer.writerows(rows)
                                    
                                    logging.info(f"Updated CSV with email for {agent_name}: {agent_email}")
                                except Exception as csv_error:
                                    logging.error(f"Error updating CSV file: {str(csv_error)}")
                            else:
                                logging.warning(f"Could not find email address for {agent_name} after trying {len(name_combinations)} name combinations")
                            
                            # Add a delay between agents
                            delay = random.uniform(1.0, 3.0)
                            logging.info(f"Waiting {delay:.1f} seconds before next agent search...")
                            time.sleep(delay)
                    
                    except Exception as e:
                        logging.error(f"Error processing agent at index {index}: {str(e)}")
                        continue
            else:
                logging.warning("No agents found in the CSV file")
                
        except Exception as e:
            logging.error(f"Error in Nestfully agent search: {str(e)}")
            # We're using the existing browser so no special cleanup is needed here
    finally:
        # Use the close method only if there's still an active driver
        try:
            bot.close()
        except:
            pass
        # Add a note to the log file that the report is available
        logging.info(f"Complete scraping report is available in: {os.path.abspath(log_filename)}")
