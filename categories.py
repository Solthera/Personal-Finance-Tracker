import uuid
from connection import get_spreadsheet
import pandas as pd

CATEGORY_COLUMNS = ["id", "nama", "budget_limit"]


def _has_header_row(first_row: list[str]) -> bool:
    first = [(c or "").strip().lower() for c in first_row[: len(CATEGORY_COLUMNS)]]
    expected = [c.lower() for c in CATEGORY_COLUMNS]
    return first == expected


def _normalize_row(row: list[str]) -> list[str]:
    padded = list(row) + [""] * len(CATEGORY_COLUMNS)
    return padded[: len(CATEGORY_COLUMNS)]


def add_categories(nama, budget_limit):
    spreadsheet = get_spreadsheet()
    sheet = spreadsheet.worksheet("categories")
    
    row = [
        str(uuid.uuid4()),
        nama,
        budget_limit
    ]
    
    sheet.append_row(row)
    return True

def get_categories():
    spreadsheet = get_spreadsheet()
    sheet = spreadsheet.worksheet("categories")
    
    # Hindari `get_all_records()` karena bisa error kalau header row ada kolom kosong/duplikat.
    values = sheet.get_all_values()
    if not values:
        return pd.DataFrame(columns=CATEGORY_COLUMNS)

    start_index = 1 if _has_header_row(values[0]) else 0
    rows = values[start_index:]
    if not rows:
        return pd.DataFrame(columns=CATEGORY_COLUMNS)

    normalized = [_normalize_row(r) for r in rows]
    df = pd.DataFrame(normalized, columns=CATEGORY_COLUMNS)
    df["budget_limit"] = pd.to_numeric(df["budget_limit"], errors="coerce").fillna(0)
    return df
