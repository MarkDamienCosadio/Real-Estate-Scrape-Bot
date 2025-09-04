from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import logging
import os
import time

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_google_sheets_service():
    """Gets Google Sheets service using service account credentials."""
    try:
        credentials = Credentials.from_service_account_file(
            'service_account.json',
            scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except Exception as e:
        logging.error(f"Error building Google Sheets service: {str(e)}")
        if not os.path.exists('service_account.json'):
            logging.error("service_account.json not found. Please follow the setup instructions.")
        return None

    try:
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        logging.error(f"Error building Google Sheets service: {str(e)}")
        return None

def create_new_spreadsheet(service, title="Zillow Listings"):
    """Creates a new Google Spreadsheet and returns its ID."""
    try:
        spreadsheet = {
            'properties': {
                'title': title
            }
        }
        spreadsheet = service.spreadsheets().create(body=spreadsheet,
                                                  fields='spreadsheetId').execute()
        logging.info(f"Created new spreadsheet with ID: {spreadsheet.get('spreadsheetId')}")
        return spreadsheet.get('spreadsheetId')
    except Exception as e:
        logging.error(f"Error creating new spreadsheet: {str(e)}")
        return None

def update_sheet_data(service, spreadsheet_id, data, range_name='A1'):
    """Updates the spreadsheet with the provided data."""
    try:
        body = {
            'values': data
        }
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        logging.info(f"Updated spreadsheet {spreadsheet_id}")
        return True
    except Exception as e:
        logging.error(f"Error updating spreadsheet: {str(e)}")
        return False

def save_to_google_sheets(data, spreadsheet_name="Zillow Listings"):
    """Main function to save data to Google Sheets."""
    service = get_google_sheets_service()
    if not service:
        logging.error("Could not create Google Sheets service")
        return False
        
    spreadsheet_id = create_new_spreadsheet(service, spreadsheet_name)
    if not spreadsheet_id:
        logging.error("Could not create new spreadsheet")
        return False
        
    # Convert DataFrame to list of lists for Google Sheets
    data_values = [data.columns.values.tolist()] + data.values.tolist()
    
    if update_sheet_data(service, spreadsheet_id, data_values):
        logging.info(f"Successfully saved data to Google Sheets. Spreadsheet ID: {spreadsheet_id}")
        return spreadsheet_id
    return False
