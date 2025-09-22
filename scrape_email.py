import os
import csv
import time
import random
import logging
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# This script assumes you have a Selenium WebDriver instance called 'driver' already running
# and a CSV file with agent names in the column 'AGENT_NAME'.
# You must pass the driver and csv_file path to the main function.

def scrape_nestfully_emails(driver, csv_file, log_filename='scrape_report.log'):
    logging.info("Starting Nestfully agent search...")
    agent_data = []
    if os.path.exists(csv_file):
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['AGENT_NAME']:
                    agent_data.append(row)
    if not agent_data:
        logging.warning("No agents found in the CSV file")
        return
    logging.info(f"Found {len(agent_data)} agents in CSV to search on Nestfully")
    for index, agent_row in enumerate(agent_data):
        try:
            agent_name = agent_row['AGENT_NAME'].strip()
            if not agent_name:
                continue
            name_parts = agent_name.split()
            if len(name_parts) < 2:
                continue
            name_combinations = []
            name_combinations.append({'first_name': name_parts[0], 'last_name': name_parts[-1]})
            if len(name_parts) == 3:
                name_combinations.append({'first_name': name_parts[0], 'last_name': ' '.join(name_parts[1:])})
                name_combinations.append({'first_name': ' '.join(name_parts[:2]), 'last_name': ' '.join(name_parts[2:])})
            elif len(name_parts) >= 4:
                name_combinations = []
                name_combinations.append({'first_name': name_parts[0], 'last_name': name_parts[-1]})
                name_combinations.append({'first_name': ' '.join(name_parts[:2]), 'last_name': name_parts[-1]})
                name_combinations.append({'first_name': ' '.join(name_parts[:2]), 'last_name': ' '.join(name_parts[2:])})
                name_combinations.append({'first_name': ' '.join(name_parts[:3]), 'last_name': name_parts[-1]})
                name_combinations.append({'first_name': name_parts[0], 'last_name': ' '.join(name_parts[1:])})
            logging.info(f"Will try {len(name_combinations)} name combinations for agent: {agent_name} ({index+1}/{len(agent_data)})")
            agent_found = False
            agent_email = None
            for combo_idx, combo in enumerate(name_combinations):
                if agent_found:
                    break
                first_name = combo['first_name']
                last_name = combo['last_name']
                logging.info(f"Trying name combination {combo_idx+1}: '{first_name}' '{last_name}'")
                driver.get("https://www.nestfully.com/agentsearch/search.aspx")
                time.sleep(random.uniform(1.0, 3.0))
                wait = WebDriverWait(driver, 10)
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                try:
                    first_name_selectors = [
                        (By.ID, "Master_FirstName"),
                        (By.XPATH, "//input[@placeholder='First Name...']"),
                        (By.XPATH, "//input[contains(@name, 'FirstName')]") ,
                        (By.XPATH, "//input[contains(@id, 'FirstName')]") ,
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
                    last_name_selectors = [
                        (By.ID, "Master_LastName"),
                        (By.XPATH, "//input[@placeholder='Last Name...']"),
                        (By.XPATH, "//input[contains(@name, 'LastName')]") ,
                        (By.XPATH, "//input[contains(@id, 'LastName')]") ,
                        (By.XPATH, "//label[contains(text(), 'Last')]/following-sibling::input"),
                        (By.XPATH, "//label[contains(text(), 'Last')]/..//input")
                    ]
                    last_name_field = None
                    for selector in last_name_selectors:
                        try:
                            last_name_field = driver.find_element(*selector)
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
                    last_name_field.send_keys(Keys.RETURN)
                    logging.info(f"Pressed Enter key to submit the search for combination {combo_idx+1}")
                except Exception as e:
                    logging.error(f"Error filling form with combination {combo_idx+1}: {str(e)}")
                    continue
                time.sleep(random.uniform(1.0, 3.0))
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                try:
                    agent_link_selectors = [
                        f"//a[contains(text(), '{first_name}') and contains(text(), '{last_name}')]",
