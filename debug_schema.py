#!/usr/bin/env python
"""
Debug script to test schema.org data extraction from Zillow listings
"""

import argparse
import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from zillow_scraper_clean import ZillowScraper

# Set logging level to debug for detailed output
logging.basicConfig(level=logging.DEBUG)

def main():
    """Main function to test schema extraction on one page only"""
    parser = argparse.ArgumentParser(description="Test schema.org data extraction from Zillow listings")
    parser.add_argument("--zipcode", type=str, default="33009", help="Zipcode to search")
    
    args = parser.parse_args()
    
    # Create scraper instance with debug mode
    scraper = ZillowScraper(
        first_page_only=True,  # Only test first page
        keep_browser_open=True,  # Keep browser open to see results
        debug_all_li=True  # Process all li elements
    )
    
    # Open Zillow and search for the zipcode
    scraper.driver.get(f"https://www.zillow.com/homes/{args.zipcode}_rb/")
    
    # Wait for page to load
    wait = WebDriverWait(scraper.driver, 15)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#grid-search-results")))
    time.sleep(3)  # Additional wait for all content to load
    
    # Find the grid container
    container = scraper.driver.find_element(By.CSS_SELECTOR, "#grid-search-results > ul")
    
    # Find all li elements
    listing_elements = container.find_elements(By.TAG_NAME, "li")
    
    print(f"Found {len(listing_elements)} li elements")
    
    # Test each li element for schema.org data
    for idx, element in enumerate(listing_elements, start=1):
        try:
            print(f"\n===== Testing Element {idx} =====")
            
            # Check if it's a valid property card
            is_valid = scraper.is_valid_property_card(element)
            print(f"Is valid property card: {is_valid}")
            
            # Extract schema data
            schema_data = scraper.extract_schema_data(element)
            if schema_data:
                print(f"Schema data found: {schema_data}")
            else:
                print("No schema data found")
            
            # Print the element's class for reference
            try:
                class_name = element.get_attribute("class")
                print(f"Element class: {class_name}")
            except:
                print("Couldn't get element class")
            
        except Exception as e:
            print(f"Error testing element {idx}: {str(e)}")
    
    # Keep browser open for manual inspection
    input("Press Enter to close browser and exit...")

if __name__ == "__main__":
    main()
