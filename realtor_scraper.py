import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import csv
import re

ZIPCODES = [
    '33009', '33019', '33119', '33128', '33129', '33130',
    '33131', '33139', '33140', '33141', '33149', '33154',
    '33160', '33180', '33239'
]

def setup_browser():
    logging.info("Setting up browser...")
    options = uc.ChromeOptions()
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-gpu')
    driver = uc.Chrome(options=options, use_subprocess=True)
    logging.info("Browser launched.")
    # Set window to 1/4 of the screen and position it in the lower-right corner
    import ctypes
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    window_width = int(screen_width / 2)
    window_height = int(screen_height / 2)
    window_x = screen_width - window_width
    window_y = screen_height - window_height
    driver.set_window_rect(window_x, window_y, window_width, window_height)
    logging.info(f"Set window size to {window_width}x{window_height} at position ({window_x}, {window_y})")
    return driver

def extract_mls(driver):
    """Extract MLS number using multiple strategies"""
    mls_patterns = [
        # Pattern 1: Look for elements containing "MLS"
        "//*[contains(translate(text(), 'MLS', 'mls'), 'mls')]",
        # Pattern 2: Look for elements containing "Listing ID" or "Property ID"
        "//*[contains(translate(text(), 'LISTINGID', 'listingid'), 'listing id')]",
        "//*[contains(translate(text(), 'PROPERTYID', 'propertyid'), 'property id')]",
        # Pattern 3: Look for ID-like patterns in spans and divs
        "//span[contains(@class, 'id') or contains(@class, 'mls')]",
        "//div[contains(@class, 'id') or contains(@class, 'mls')]",
    ]
    
    # Try each pattern
    for pattern in mls_patterns:
        try:
            elements = driver.find_elements(By.XPATH, pattern)
            for elem in elements:
                text = elem.text.strip()
                if not text or text.lower() == 'matrix':
                    continue
                # Pattern 1: MLS # A12345678 or similar
                mls_match = re.search(r'MLS[#:\s]*([A-Z0-9\-]{6,})', text, re.IGNORECASE)
                if mls_match:
                    candidate = mls_match.group(1).strip()
                    if candidate.lower() != 'matrix':
                        if candidate != '2121192':
                            return candidate
                # Pattern 2: Just the ID itself (A followed by numbers)
                if re.match(r'^A\d{6,}$', text) and text.lower() != 'matrix' and text != '2121192':
                    return text
                # Pattern 3: Any alphanumeric ID of reasonable length, not 'Matrix' or '2121192'
                if re.match(r'^[A-Z0-9\-]{6,}$', text) and len(text) >= 6 and text.lower() != 'matrix' and text != '2121192':
                    return text
        except Exception as e:
            continue

    # Final fallback: scan all text on page for MLS-like patterns
    mls_candidate = ''
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        page_text = body.text
        fallback_patterns = [
            r'MLS[#:\s]*([A-Z0-9\-]{6,})',
            r'Listing ID[#:\s]*([A-Z0-9\-]{6,})',
            r'Property ID[#:\s]*([A-Z0-9\-]{6,})',
            r'\b(A\d{6,})\b',
            r'\b([A-Z]{2,3}\d{6,})\b'  # For patterns like RX-10958722
        ]
        for pattern in fallback_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                if match.lower() != 'matrix' and match != '2121192':
                    mls_candidate = match
                    break
            if mls_candidate:
                break
    except Exception as e:
        logging.warning(f"Error in final MLS fallback: {e}")

    # If still not found, use property_id from meta div as last fallback
    if not mls_candidate:
        try:
            property_id = driver.find_element(By.XPATH, "//div[@class='meta']/div[2]").text.strip()
            if property_id and property_id != '2121192':
                mls_candidate = property_id
        except Exception:
            pass

    return mls_candidate

def search_zipcode(driver, zipcode):
    """Scrape Realtor.com for a given zipcode and save results to CSV."""
    # Prepare CSV file
    csv_file = 'realtor_results.csv'
    headers = ['ZIPCODE', 'MLS', 'PRICE','ADDRESS', 'BEDS', 'BATHS', 'SQFT', 'URL', 'MAPS_URL', 'DAYS_ON_MARKET', 'AGENT_NAME', 'AGENT_PHONE', 'EMAIL']
    import os
    if not os.path.exists(csv_file):
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

    # Load already-saved URLs from CSV
    saved_urls = set()
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'URL' in row and row['URL']:
                    saved_urls.add(row['URL'])
    except Exception:
        pass

    # Go to Realtor.com search page for the zipcode, with filters and sorting by Newest
    search_url = f"https://www.realtor.com/realestateandhomes-search/{zipcode}/beds-2/price-200000-na/sby-6"
    driver.get(search_url)
    time.sleep(2)

    # Scroll only to elements with '/realestateandhomes-detail/' in href
    seen_hrefs = set()
    for _ in range(20):
        anchors = driver.find_elements(By.XPATH, "//a[contains(@class, 'LinkComponent_anchor__') and contains(@href, '/realestateandhomes-detail/')]")
        for a in anchors:
            href = a.get_attribute('href')
            if href and '/realestateandhomes-detail/' in href and href not in seen_hrefs:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", a)
                time.sleep(0.5)
                seen_hrefs.add(href)
        time.sleep(0.5)

    # Collect anchor elements for all unique hrefs, preserving page order
    filtered_anchors = []
    anchors = driver.find_elements(By.XPATH, "//a[contains(@class, 'LinkComponent_anchor__') and contains(@href, '/realestateandhomes-detail/')]")
    seen = set()
    for a in anchors:
        href = a.get_attribute('href')
        if href and href not in seen_hrefs:
            continue  # Only process discovered hrefs
        if href and href not in seen:
            filtered_anchors.append(a)
            seen.add(href)

    # After scrolling, open and extract data from every property card
    main_window = driver.current_window_handle
    # Find all property cards using the recommended CSS selector
    cards = driver.find_elements(By.CSS_SELECTOR, "div.BasePropertyCard_propertyCardWrap__gtWK6[data-listing-id][data-property-id]")
    logging.info(f"Found {len(cards)} property cards to process.")
    hrefs = []
    for card in cards:
        try:
            anchor = card.find_element(By.XPATH, ".//a[contains(@href, '/realestateandhomes-detail/')]")
            href = anchor.get_attribute('href')
            if href:
                hrefs.append(href)
        except Exception as e:
            logging.debug(f"Card anchor extraction error: {e}")
    logging.info(f"Found {len(hrefs)} property card hrefs to process.")

    # Extract data from each property card by navigating in the same tab
    search_results_url = driver.current_url
    anchors_xpath = "//a[contains(@class, 'LinkComponent_anchor__') and contains(@href, '/realestateandhomes-detail/')]"
    seen_hrefs = set()
    hrefs = []
    for _ in range(20):
        try:
            anchors = WebDriverWait(driver, 4).until(
                EC.presence_of_all_elements_located((By.XPATH, anchors_xpath)))
        except Exception:
            anchors = driver.find_elements(By.XPATH, anchors_xpath)
        for a in anchors:
            href = a.get_attribute('href')
            if href and '/realestateandhomes-detail/' in href and href not in seen_hrefs:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", a)
                time.sleep(0.2)
                seen_hrefs.add(href)
                hrefs.append(href)
        time.sleep(0.2)

    # Now iterate over hrefs for scraping
    page_num = 1
    listings_processed = 0
    MAX_LISTINGS = 20
    while True:
        consecutive_skips = 0
        for href in hrefs:
            if listings_processed >= MAX_LISTINGS:
                logging.info(f"Reached {MAX_LISTINGS} listings for zipcode {zipcode}. Stopping.")
                return
            if href in saved_urls:
                logging.info(f"Skipping already-saved property: {href}")
                consecutive_skips += 1
                if consecutive_skips >= 3:
                    logging.info(f"Skipped 3 consecutive listings for zipcode {zipcode}. Assuming latest listings reached. Stopping.")
                    return
                continue
            else:
                consecutive_skips = 0
            try:
                logging.info(f"Navigating to property card: {href}")
                driver.get(href)
                data = {}
                data['ZIPCODE'] = zipcode
                data['URL'] = href
                data['MLS'] = extract_mls(driver)
                if not data['MLS']:
                    logging.warning("MLS not found for this listing.")
                try:
                    address_elem = driver.find_element(By.XPATH, "//h1[contains(@class,'sc-fa97e35a-3')]")
                    data['ADDRESS'] = address_elem.text.strip()
                except Exception:
                    data['ADDRESS'] = ''
                # Extract price
                try:
                    price_elem = driver.find_element(By.XPATH, "//span[contains(@class, 'base__StyledType-rui__sc-18muj27-0') and contains(@class, 'idlIli')]")
                    data['PRICE'] = price_elem.text.strip()
                except Exception:
                    data['PRICE'] = ''
                try:
                    beds_elem = driver.find_element(By.XPATH, "//li[@data-testid='property-meta-beds']//span[@data-testid='meta-value']")
                    data['BEDS'] = beds_elem.text.strip()
                except Exception:
                    data['BEDS'] = ''
                try:
                    baths_elem = driver.find_element(By.XPATH, "//li[@data-testid='property-meta-baths']//span[@data-testid='meta-value']")
                    data['BATHS'] = baths_elem.text.strip()
                except Exception:
                    data['BATHS'] = ''
                try:
                    sqft_elem = driver.find_element(By.XPATH, "//span[@class='meta-value' and @data-testid='meta-value']")
                    data['SQFT'] = sqft_elem.text.strip()
                except Exception:
                    data['SQFT'] = ''
                # Extract agent name
                try:
                    agent_elem = driver.find_element(By.XPATH, "//a[@data-testid='provider-link']")
                    data['AGENT_NAME'] = agent_elem.text.strip()
                except Exception:
                    try:
                        # Fallback to previous method if provider-link not found
                        agent_elem = driver.find_element(By.XPATH, "//li[contains(., 'Listed by')]/span[last()]")
                        data['AGENT_NAME'] = agent_elem.text.strip()
                    except Exception:
                        data['AGENT_NAME'] = ''
                # Extract days on market
                try:
                    days_elem = driver.find_element(By.XPATH, "//li[contains(@class, 'sc-c1d03842-0')]//p[contains(text(), 'hour') or contains(text(), 'day')]")
                    data['DAYS_ON_MARKET'] = days_elem.text.strip()
                except Exception:
                    data['DAYS_ON_MARKET'] = ''
                # Extract agent phone number
                try:
                    phone_elem = driver.find_element(By.XPATH, "//a[@data-testid='office-phone-link']")
                    data['AGENT_PHONE'] = phone_elem.text.strip()
                except Exception:
                    data['AGENT_PHONE'] = ''
                # Update headers if AGENT_NAME or AGENT_PHONE not present
                if 'AGENT_NAME' not in headers:
                    headers.append('AGENT_NAME')
                if 'AGENT_PHONE' not in headers:
                    headers.append('AGENT_PHONE')
                if 'EMAIL' not in data:
                    data['EMAIL'] = ''
                # Construct Google Maps link from address if available
                if data['ADDRESS']:
                    maps_query = data['ADDRESS'].replace(' ', '+')
                    data['MAPS_URL'] = f"https://www.google.com/maps/search/?api=1&query={maps_query}"
                else:
                    data['MAPS_URL'] = ''
                # Update headers if AGENT_NAME not present
                if 'AGENT_NAME' not in headers:
                    headers.append('AGENT_NAME')
                with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writerow(data)
                logging.info(f"Extracted and saved property data: {data}")
                listings_processed += 1
                saved_urls.add(href)
                # Return to search results page
                driver.get(search_results_url)
            except Exception as e:
                logging.error(f"Error processing property card: {e}")
        # After all listings, try to go to next page
        if listings_processed >= MAX_LISTINGS:
            logging.info(f"Reached {MAX_LISTINGS} listings for zipcode {zipcode}. Stopping.")
            break
        try:
            next_page_num = page_num + 1
            # Scroll pagination bar into view first
            try:
                pagination_bar = driver.find_element(By.XPATH, "//nav[contains(@class, 'pagination')] | //ul[contains(@class, 'pagination')]")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", pagination_bar)
                time.sleep(0.5)
            except Exception:
                pass

            next_btn = None
            # Try numbered page link by aria-label
            try:
                next_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        f"//a[contains(@class, 'pagination-item') and contains(@aria-label, 'Go to page {next_page_num}')]")
                    )
                )
            except Exception:
                pass
            # Fallback: try numbered page link by text content
            if not next_btn:
                try:
                    next_btn = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            f"//a[contains(@class, 'pagination-item') and normalize-space(text())='{next_page_num}']"
                        ))
                    )
                except Exception:
                    pass
            # Fallback: try a 'Next' button
            if not next_btn:
                try:
                    next_btn = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((
                            By.XPATH,
                            "//a[contains(@class, 'pagination-item') and (contains(text(), 'Next') or contains(@aria-label, 'Next'))]"
                        ))
                    )
                except Exception:
                    pass
            if next_btn and next_btn.is_displayed() and next_btn.is_enabled():
                # Wait before clicking next page
                time.sleep(2)
                next_btn.click()
                logging.info(f"Successfully clicked next page link for page {next_page_num}.")
                time.sleep(2)
                search_results_url = driver.current_url
                # Scroll to reveal all property cards on the new page
                seen_hrefs = set()
                for _ in range(20):
                    anchors = driver.find_elements(By.XPATH, "//a[contains(@class, 'LinkComponent_anchor__') and contains(@href, '/realestateandhomes-detail/')]")
                    for a in anchors:
                        href = a.get_attribute('href')
                        if href and '/realestateandhomes-detail/' in href and href not in seen_hrefs:
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", a)
                            time.sleep(0.5)
                            seen_hrefs.add(href)
                    time.sleep(0.5)
                # Collect anchor elements for all unique hrefs, preserving page order
                filtered_anchors = []
                anchors = driver.find_elements(By.XPATH, "//a[contains(@class, 'LinkComponent_anchor__') and contains(@href, '/realestateandhomes-detail/')]")
                seen = set()
                for a in anchors:
                    href = a.get_attribute('href')
                    if href and href not in seen_hrefs:
                        continue  # Only process discovered hrefs
                    if href and href not in seen:
                        filtered_anchors.append(a)
                        seen.add(href)
                # Find all property cards
                cards = driver.find_elements(By.CSS_SELECTOR, "div.BasePropertyCard_propertyCardWrap__gtWK6[data-listing-id][data-property-id]")
                logging.info(f"Found {len(cards)} property cards to process on page {next_page_num}.")
                hrefs = []
                for card in cards:
                    try:
                        anchor = card.find_element(By.XPATH, ".//a[contains(@href, '/realestateandhomes-detail/')]")
                        href = anchor.get_attribute('href')
                        if href:
                            hrefs.append(href)
                    except Exception as e:
                        logging.debug(f"Card anchor extraction error: {e}")
                page_num += 1
            else:
                logging.info("Next page link not enabled, not visible, or not found. Scraping complete.")
                break
        except Exception:
            logging.info("No more pages found or next page link not clickable. Scraping complete.")
            break

def main():
    log_filename = 'realtor_scraper.log'
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

    driver = None
    try:
        logging.info("Starting Realtor.com scraper...")
        driver = setup_browser()
        for zipcode in ZIPCODES:
            logging.info(f"Processing zipcode: {zipcode}")
            search_zipcode(driver, zipcode)
        logging.info("All zipcodes processed. Applying cleaner logic to realtor_results.csv...")
        # Cleaner logic (copied from redfin_scraper.py)
        import pandas as pd
        import re
        import os
        csv_file = 'realtor_results.csv'
        log_file = 'realtor_scraper_cleaner.log'
        def valid_zipcode(val):
            return bool(re.match(r'^\d{5}$', str(val).strip()))
        def valid_mls(val):
            s = str(val).strip()
            return bool(re.match(r'^[A-Za-z0-9\-]+$', s)) and s and s.lower() != 'source'
        def valid_price(val):
            s = str(val).replace('$', '').replace(',', '').strip()
            return bool(re.match(r'^\d+(\.\d+)?$', s)) and float(s) > 0
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            initial_count = len(df)
            deleted_rows = []
            # Clean ZIPCODE
            if 'ZIPCODE' in df.columns:
                mask_zip = df['ZIPCODE'].apply(valid_zipcode)
                deleted_rows.extend(df[~mask_zip].to_dict('records'))
                df = df[mask_zip]
            # Clean MLS: remove rows where MLS is missing or invalid
            if 'MLS' in df.columns:
                mask_mls = df['MLS'].apply(lambda x: pd.notna(x) and str(x).strip() != '' and valid_mls(x))
                deleted_rows.extend(df[~mask_mls].to_dict('records'))
                df = df[mask_mls]
            # Clean PRICE
            if 'PRICE' in df.columns:
                mask_price = df['PRICE'].apply(valid_price)
                deleted_rows.extend(df[~mask_price].to_dict('records'))
                df = df[mask_price]
            final_count = len(df)
            deleted_count = initial_count - final_count
            cleaned_path = csv_file.replace('.csv', '_cleaned.csv')
            df.to_csv(cleaned_path, index=False)
            # Log deleted rows
            with open(log_file, 'a', encoding='utf-8') as logf:
                if deleted_count > 0:
                    logf.write(f"{deleted_count} rows deleted from {csv_file}.\n")
                    for row in deleted_rows:
                        logf.write(f"Deleted from {csv_file}: {row}\n")
            print(f"{deleted_count} rows deleted from {csv_file}. Cleaned file saved as {cleaned_path}.")
        else:
            print(f"{csv_file} not found for cleaning.")
        logging.info("Cleaning complete. See realtor_scraper_cleaner.log for details.")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()