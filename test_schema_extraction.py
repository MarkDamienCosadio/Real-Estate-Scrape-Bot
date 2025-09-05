#!/usr/bin/env python
"""
Test script for running the Zillow scraper with enhanced schema.org data extraction
"""

import argparse
from zillow_scraper_clean import ZillowScraper

def main():
    """Main function to run the Zillow scraper with improved listing detection"""
    parser = argparse.ArgumentParser(description="Run Zillow scraper with enhanced schema extraction")
    parser.add_argument("--zipcode", type=str, help="Zipcode to search")
    parser.add_argument("--first-page-only", action="store_true", help="Only process the first page of results")
    parser.add_argument("--keep-browser-open", action="store_true", help="Keep the browser open after scraping")
    parser.add_argument("--max-listings", type=int, default=0, help="Maximum number of listings to process (0 for all)")
    parser.add_argument("--debug-all-li", action="store_true", help="Process all <li> elements regardless of validation")
    
    args = parser.parse_args()
    
    # Create scraper instance with command line options
    scraper = ZillowScraper(
        first_page_only=args.first_page_only,
        keep_browser_open=args.keep_browser_open,
        max_listings=args.max_listings,
        debug_all_li=args.debug_all_li
    )
    
    # Run the scraper with specified zipcode or default
    zipcode = args.zipcode if args.zipcode else "33009"
    scraper.run(zipcode)

if __name__ == "__main__":
    main()
