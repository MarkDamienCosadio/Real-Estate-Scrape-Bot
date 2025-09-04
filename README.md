# Real Estate Scrape Bot

A robust web scraping tool designed to extract property information from Zillow. Built with Python and Selenium, this bot navigates through property listings, applies filters, and extracts detailed information about each listing.

## Features

- Search properties by zipcode
- Apply filters (price range, number of bedrooms)
- Sort listings by newest first
- Extract comprehensive property details:
  - Price
  - Address
  - Number of beds and baths
  - Square footage
  - MLS number
  - Days on market
  - Agent information (name and contact)
  - Listing URL
  - Google Maps URL for the property
- Save data to CSV for easy analysis

## Requirements

- Python 3.7+
- Chrome browser
- Undetected Chromedriver
- Selenium

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the script with:

```
python zillow_scraper_clean.py
```

Data will be saved to `zillow_results.csv` in the project directory.

## Customization

- Modify the `ZIPCODES` list to target specific areas
- Adjust price filters in the `apply_filters` method
- Change the number of bedrooms filter as needed

## Note

This tool is designed for educational purposes and personal use. Please respect Zillow's terms of service and rate limits when using this tool.

## Google Sheets Integration

This project also supports Google Sheets integration. To enable:

1. Create a Google Cloud project and enable the Google Sheets API
2. Create a service account and download the JSON credentials
3. Save the credentials as `credentials.json` in the project directory
4. Share your target Google Sheet with the service account email
