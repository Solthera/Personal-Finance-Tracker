from __future__ import annotations

import gspread
import streamlit as st

from repositories.categories import get_categories
from repositories.goals import get_goals
from services.gsheet_errors import show_spreadsheet_not_found, show_worksheet_not_found
from repositories.transactions import get_transactions


def load_transactions(*, stop: bool = False):
    try:
        return get_transactions()
    except gspread.exceptions.SpreadsheetNotFound:
        show_spreadsheet_not_found()
    except gspread.exceptions.WorksheetNotFound:
        show_worksheet_not_found("transactions")
    if stop:
        st.stop()
    return None


def load_categories(*, stop: bool = False):
    try:
        return get_categories()
    except gspread.exceptions.SpreadsheetNotFound:
        show_spreadsheet_not_found()
    except gspread.exceptions.WorksheetNotFound:
        show_worksheet_not_found("categories")
    if stop:
        st.stop()
    return None


def load_goals(*, stop: bool = False):
    try:
        return get_goals()
    except gspread.exceptions.SpreadsheetNotFound:
        show_spreadsheet_not_found()
    except gspread.exceptions.WorksheetNotFound:
        show_worksheet_not_found("goals")
    if stop:
        st.stop()
    return None
