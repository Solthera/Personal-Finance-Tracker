import gspread
import os
from google.oauth2.service_account import Credentials
from functools import lru_cache

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]


@lru_cache(maxsize=1)
def get_spreadsheet():
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
    spreadsheet_id = os.getenv("SPREADSHEET_ID", "").strip()
    spreadsheet_name = os.getenv("SPREADSHEET_NAME", "personal-finance-tracker").strip()

    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    if spreadsheet_id:
        return client.open_by_key(spreadsheet_id)
    return client.open(spreadsheet_name)
