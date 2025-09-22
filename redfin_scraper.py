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
    # Set window to 1/4 of the screen and position it in the upper left corner
    import ctypes
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    window_width = int(screen_width / 2)
    window_height = int(screen_height / 2)
    window_x = 0
    window_y = 0
    driver.set_window_rect(window_x, window_y, window_width, window_height)
    logging.info(f"Set window size to {window_width}x{window_height} at position ({window_x}, {window_y})")
    return driver

def extract_mls(driver):
    """Extract MLS number from Redfin property page"""
    try:
        mls_elem = driver.find_element(By.XPATH, "//div[contains(text(), 'MLS#')]")
        mls_match = re.search(r'MLS#\s*([A-Z0-9\-]+)', mls_elem.text)
        if mls_match:
            return mls_match.group(1)
    except Exception:
        pass
    return ''

def search_zipcode(driver, zipcode):
    """Scrape Redfin for a given zipcode and save results to CSV."""
    csv_file = 'redfin_results.csv'
    headers = ['ZIPCODE', 'MLS', 'PRICE', 'ADDRESS', 'BEDS', 'BATHS', 'SQFT', 'URL', 'MAPS_URL', 'DAYS_ON_MARKET', 'AGENT_NAME', 'AGENT_PHONE', 'EMAIL']
    import os
    # Always ensure headers are present in the CSV
    # Only write headers if file does not exist
    if not os.path.exists(csv_file):
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
    saved_urls = set()
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'URL' in row and row['URL']:
                    saved_urls.add(row['URL'])
    except Exception:
        pass
    search_url = f"https://www.redfin.com/zipcode/{zipcode}/filter/sort=lo-days,min-price=200k,min-beds=2"
    driver.get(search_url)
    time.sleep(2)
    MAX_LISTINGS = 20
    listings_processed = 0
    page_num = 1
    while True:
        # Find all property cards
        cards = driver.find_elements(By.CSS_SELECTOR, "div.HomeCardContainer")
        logging.info(f"Found {len(cards)} property cards to process on page {page_num}.")
        hrefs = []
        for card in cards:
            try:
                anchor = card.find_element(By.XPATH, ".//a[contains(@href, '/home/')]")
                href = anchor.get_attribute('href')
                if href:
                    hrefs.append(href)
            except Exception as e:
                logging.debug(f"Card anchor extraction error: {e}")
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
                try:
                    mls_elem = driver.find_element(By.CSS_SELECTOR, "span.ListingSource--mlsId")
                    mls_text = mls_elem.text.strip()
                    if mls_text.startswith('#'):
                        mls_text = mls_text[1:].strip()
                    data['MLS'] = mls_text
                except Exception:
                    data['MLS'] = extract_mls(driver)
                try:
                    address_elem = driver.find_element(By.CSS_SELECTOR, "h1.full-address.addressBannerRevamp.street-address")
                    data['ADDRESS'] = address_elem.text.strip()
                except Exception:
                    data['ADDRESS'] = ''
                try:
                    price_elem = driver.find_element(By.CSS_SELECTOR, "div.statsValue.price")
                    data['PRICE'] = price_elem.text.strip()
                except Exception:
                    data['PRICE'] = ''
                try:
                    beds_elem = driver.find_element(By.CSS_SELECTOR, "div.stat-block.beds-section div.statsValue")
                    data['BEDS'] = beds_elem.text.strip()
                except Exception:
                    data['BEDS'] = ''
                try:
                    baths_elem = driver.find_element(By.CSS_SELECTOR, "div.stat-block.baths-section span.bp-DefinitionFlyout.bath-flyout.bp-DefinitionFlyout__underline")
                    data['BATHS'] = baths_elem.text.strip()
                except Exception:
                    data['BATHS'] = ''
                try:
                    sqft_elem = driver.find_element(By.CSS_SELECTOR, "div.stat-block.sqft-section span.statsValue")
                    data['SQFT'] = sqft_elem.text.strip()
                except Exception:
                    data['SQFT'] = ''
                try:
                    agent_elem = driver.find_element(By.CSS_SELECTOR, "span.agent-basic-details--heading span")
                    data['AGENT_NAME'] = agent_elem.text.strip()
                except Exception:
                    data['AGENT_NAME'] = ''
                try:
                    phone_elem = driver.find_element(By.CSS_SELECTOR, "span[data-rf-test-id='agentInfoItem-agentPhoneNumber']")
                    phone_text = phone_elem.text.strip()
                    # Remove '(agent)' if present
                    phone_text = phone_text.replace('(agent)', '').strip()
                    data['AGENT_PHONE'] = phone_text
                except Exception:
                    data['AGENT_PHONE'] = ''
                data['EMAIL'] = ''
                try:
                    days_elem = driver.find_element(By.CSS_SELECTOR, "div.keyDetails-row div.keyDetails-value span.valueText")
                    data['DAYS_ON_MARKET'] = days_elem.text.strip()
                except Exception:
                    data['DAYS_ON_MARKET'] = ''
                if data['ADDRESS']:
                    maps_query = data['ADDRESS'].replace(' ', '+')
                    data['MAPS_URL'] = f"https://www.google.com/maps/search/?api=1&query={maps_query}"
                else:
                    data['MAPS_URL'] = ''
                with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writerow(data)
                logging.info(f"Extracted and saved property data: {data}")
                listings_processed += 1
                saved_urls.add(href)
                driver.get(search_url)
            except Exception as e:
                logging.error(f"Error processing property card: {e}")
        # Try to go to next page
        try:
            next_btn = None
            try:
                next_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.PageArrow__direction--next"))
                )
            except Exception:
                pass
            if next_btn and next_btn.is_displayed() and next_btn.is_enabled():
                time.sleep(2)
                next_btn.click()
                logging.info(f"Successfully clicked next page link for page {page_num + 1}.")
                time.sleep(2)
                page_num += 1
            else:
                logging.info("Next page link not enabled, not visible, or not found. Scraping complete.")
                break
        except Exception:
            logging.info("No more pages found or next page link not clickable. Scraping complete.")
            break

def main():
    log_filename = 'redfin_scraper.log'
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
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    driver = None
    try:
        logging.info("Starting Redfin scraper...")
        driver = setup_browser()
        for zipcode in ZIPCODES:
            logging.info(f"Processing zipcode: {zipcode}")
            search_zipcode(driver, zipcode)
        logging.info("All zipcodes processed. Applying cleaner logic to redfin_results.csv...")
        # Cleaner logic
        import pandas as pd
        import re
        import os
        csv_file = 'redfin_results.csv'
        log_file = 'redfin_scraper_cleaner.log'
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
        logging.info("Cleaning complete. See redfin_scraper_cleaner.log for details.")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
