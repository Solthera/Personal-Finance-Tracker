import gspread
import os
import json
from google.oauth2.service_account import Credentials
from functools import lru_cache

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def _load_credentials(scopes):
    # 1) Local file path (dev)
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
    if os.path.isfile(credentials_path):
        return Credentials.from_service_account_file(credentials_path, scopes=scopes)

    # 2) Raw JSON via env var (recommended for Streamlit Cloud)
    raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw_json:
        info = json.loads(raw_json)
        return Credentials.from_service_account_info(info, scopes=scopes)

    # 3) Streamlit secrets (Streamlit Cloud)
    try:
        import streamlit as st  # optional dependency at runtime

        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            return Credentials.from_service_account_info(info, scopes=scopes)

        if "GOOGLE_SERVICE_ACCOUNT_JSON" in st.secrets:
            info = json.loads(str(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]))
            return Credentials.from_service_account_info(info, scopes=scopes)
    except Exception:
        pass

    raise FileNotFoundError(
        "Service account credentials tidak ditemukan. "
        "Set `GOOGLE_SERVICE_ACCOUNT_JSON` (raw JSON) atau Streamlit secrets `gcp_service_account`, "
        "atau sediakan file `credentials.json`."
    )

def _get_setting(name: str, default: str = "") -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value

    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass

    return default.strip()


@lru_cache(maxsize=1)
def get_spreadsheet():
    spreadsheet_id = _get_setting("SPREADSHEET_ID", "")
    spreadsheet_name = _get_setting("SPREADSHEET_NAME", "personal-finance-tracker")

    creds = _load_credentials(SCOPES)
    client = gspread.authorize(creds)
    if spreadsheet_id:
        return client.open_by_key(spreadsheet_id)
    return client.open(spreadsheet_name)
