import pandas as pd
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def setup_browser():
	driver = uc.Chrome()
	driver.set_window_size(1200, 800)
	return driver

def get_agent_email(driver, agent_name):
	search_url = 'https://www.nestfully.com/agentsearch/search.aspx'
	driver.get(search_url)
	time.sleep(2)
	parts = agent_name.split()
	n = len(parts)
	tried = set()
	# Build all possible combinations
	combos = []
	for i in range(1, n):
		combos.append(( ' '.join(parts[:i]), ' '.join(parts[i:]) ))
	if n > 1:
		combos.append((parts[0], ' '.join(parts[1:])))
	if n > 2:
		combos.append((' '.join(parts[:2]), ' '.join(parts[2:])))
		combos.append((parts[0], ' '.join(parts[-2:])))
	if n > 1:
		combos.append((' '.join(parts[:-1]), parts[-1]))
		combos.append((parts[0], parts[-1]))

	tried = set()
	for firstname, lastname in combos:
		combo = (firstname, lastname)
		if combo in tried:
			continue
		tried.add(combo)
		print(f"Trying: First name='{firstname}', Last name='{lastname}'")
		try:
			driver.get(search_url)
			time.sleep(1)
			first_box = driver.find_element(By.ID, 'Master_FirstName')
			last_box = driver.find_element(By.ID, 'Master_LastName')
			first_box.clear()
			last_box.clear()
			first_box.send_keys(firstname)
			last_box.send_keys(lastname)
			last_box.send_keys(Keys.RETURN)
			time.sleep(2)
			links = driver.find_elements(By.CSS_SELECTOR, 'a.ao_results_icon_text.A.detail-page')
			for link in links:
				if lastname.lower() in link.text.lower() or firstname.lower() in link.text.lower():
					link.click()
					time.sleep(2)
					try:
						email_link = driver.find_element(By.ID, 'hlAgentEmailAddress')
						email = email_link.text.strip()
						if '@' in email:
							return email
					except Exception:
						email_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '@')]")
						for elem in email_elements:
							email = elem.text.strip()
							if '@' in email:
								return email
					break  # After clicking a link, break to reload for next combo
		except Exception as e:
			print(f"Error trying combination {combo}: {e}")
			continue
	return ''
	if n > 1:
		firstname = parts[0]
		lastname = ' '.join(parts[1:])
		combo = (firstname, lastname)
		if combo not in tried:
			tried.add(combo)
			try:
				first_box = driver.find_element(By.ID, 'Master_FirstName')
				last_box = driver.find_element(By.ID, 'Master_LastName')
				first_box.clear()
				last_box.clear()
				first_box.send_keys(firstname)
				last_box.send_keys(lastname)
				last_box.send_keys(Keys.RETURN)
				time.sleep(2)
				links = driver.find_elements(By.CSS_SELECTOR, 'a.ao_results_icon_text.A.detail-page')
				for link in links:
					if lastname.lower() in link.text.lower() or firstname.lower() in link.text.lower():
						link.click()
						time.sleep(2)
						try:
							email_link = driver.find_element(By.ID, 'hlAgentEmailAddress')
							email = email_link.text.strip()
							if '@' in email:
								return email
						except Exception:
							email_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '@')]")
							for elem in email_elements:
								email = elem.text.strip()
								if '@' in email:
									return email
						driver.get(search_url)
						time.sleep(1)
			except Exception:
				pass
	# Try all but last word as first name, last word as last name
	if n > 1:
		firstname = ' '.join(parts[:-1])
		lastname = parts[-1]
		combo = (firstname, lastname)
		if combo not in tried:
			tried.add(combo)
			try:
				first_box = driver.find_element(By.ID, 'Master_FirstName')
				last_box = driver.find_element(By.ID, 'Master_LastName')
				first_box.clear()
				last_box.clear()
				first_box.send_keys(firstname)
				last_box.send_keys(lastname)
				last_box.send_keys(Keys.RETURN)
				time.sleep(2)
				links = driver.find_elements(By.CSS_SELECTOR, 'a.ao_results_icon_text.A.detail-page')
				for link in links:
					if lastname.lower() in link.text.lower() or firstname.lower() in link.text.lower():
						link.click()
						time.sleep(2)
						try:
							email_link = driver.find_element(By.ID, 'hlAgentEmailAddress')
							email = email_link.text.strip()
							if '@' in email:
								return email
						except Exception:
							email_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '@')]")
							for elem in email_elements:
								email = elem.text.strip()
								if '@' in email:
									return email
						driver.get(search_url)
						time.sleep(1)
			except Exception:
				pass
	# Try first word as first name, last word as last name
	if n > 1:
		firstname = parts[0]
		lastname = parts[-1]
		combo = (firstname, lastname)
		if combo not in tried:
			tried.add(combo)
			try:
				first_box = driver.find_element(By.ID, 'Master_FirstName')
				last_box = driver.find_element(By.ID, 'Master_LastName')
				first_box.clear()
				last_box.clear()
				first_box.send_keys(firstname)
				last_box.send_keys(lastname)
				last_box.send_keys(Keys.RETURN)
				time.sleep(2)
				links = driver.find_elements(By.CSS_SELECTOR, 'a.ao_results_icon_text.A.detail-page')
				for link in links:
					if lastname.lower() in link.text.lower() or firstname.lower() in link.text.lower():
						link.click()
						time.sleep(2)
						try:
							email_link = driver.find_element(By.ID, 'hlAgentEmailAddress')
							email = email_link.text.strip()
							if '@' in email:
								return email
						except Exception:
							email_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '@')]")
							for elem in email_elements:
								email = elem.text.strip()
								if '@' in email:
									return email
						driver.get(search_url)
						time.sleep(1)
			except Exception:
				pass
	return ''

def main():
	df = pd.read_csv('main_listing.csv')
	if 'EMAIL' not in df.columns:
		df['EMAIL'] = pd.NA
	driver = setup_browser()
	try:
		for idx, row in df.iterrows():
			agent_name = str(row.get('AGENT_NAME', '')).strip()
			if not agent_name or (pd.notna(row.get('EMAIL')) and str(row.get('EMAIL')).strip()):
				continue
			email = get_agent_email(driver, agent_name)
			if email:
				df.at[idx, 'EMAIL'] = email
			df.to_csv('main_listing.csv', index=False)
			time.sleep(1)
	finally:
		driver.quit()

if __name__ == "__main__":
	main()

