import pandas as pd
import os

# Paths to cleaned CSVs

csv_sources = {
	'zillow_results_cleaned.csv': 'ZLW',
	'realtor_results_cleaned.csv': 'RLTR',
	'redfin_results_cleaned.csv': 'RDFN'
}

# Read and concatenate all available cleaned CSVs, adding SOURCE column
dfs = []
for file, source in csv_sources.items():
	if os.path.exists(file):
		df = pd.read_csv(file)
		df['SOURCE'] = source
		dfs.append(df)
	else:
		print(f"Warning: {file} not found.")

if dfs:
	combined = pd.concat(dfs, ignore_index=True)
	# Remove fully identical rows
	combined = combined.drop_duplicates(keep='first')
	# Deduplicate by MLS, keeping the first occurrence
	if 'MLS' in combined.columns:
		combined = combined.drop_duplicates(subset=['MLS'], keep='first')
	combined.to_csv('main_listing.csv', index=False)
	print(f"Compiled {len(combined)} unique listings into main_listing.csv.")
else:
	print("No cleaned CSV files found to compile.")
