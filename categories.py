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


def _category_row_numbers(sheet, category_name: str) -> list[int]:
    values = sheet.get_all_values()
    if not values:
        return []

    has_header = _has_header_row(values[0])
    data_rows = values[1:] if has_header else values
    start_row_number = 2 if has_header else 1

    target = str(category_name or "").strip().lower()
    matches: list[int] = []
    for offset, row in enumerate(data_rows):
        normalized = _normalize_row(row)
        name_cell = str(normalized[1] or "").strip().lower()
        if name_cell and name_cell == target:
            matches.append(start_row_number + offset)
    return matches


def add_categories(nama, budget_limit):
    spreadsheet = get_spreadsheet()
    sheet = spreadsheet.worksheet("categories")

    budget_to_add = float(pd.to_numeric(budget_limit, errors="coerce") or 0)
    if budget_to_add < 0:
        budget_to_add = 0

    row_numbers = _category_row_numbers(sheet, nama)
    if not row_numbers:
        row = [str(uuid.uuid4()), str(nama).strip(), budget_to_add]
        sheet.append_row(row)
        return "created"

    # Kalau kategori sudah ada: tambah budget_limit-nya (dan rapihin duplikat kalau ada).
    total_existing = 0.0
    for row_number in row_numbers:
        current = _normalize_row(sheet.row_values(row_number))
        total_existing += float(pd.to_numeric(current[2], errors="coerce") or 0)

    new_total = total_existing + budget_to_add

    # Update baris pertama yang ditemukan
    first_row_number = row_numbers[0]
    current_first = _normalize_row(sheet.row_values(first_row_number))
    current_first[1] = str(nama).strip()
    current_first[2] = new_total
    sheet.update(f"A{first_row_number}:C{first_row_number}", [current_first[:3]])

    # Hapus duplikat lainnya (hapus dari bawah biar index gak geser)
    for row_number in sorted(row_numbers[1:], reverse=True):
        sheet.delete_rows(row_number)

    return "updated"

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

    # Dedup (kalau sudah terlanjur ada duplikat di sheet): gabungkan berdasarkan nama (case-insensitive)
    df["__nama_norm"] = df["nama"].astype(str).str.strip().str.lower()
    df = (
        df.groupby("__nama_norm", as_index=False)
        .agg({"id": "first", "nama": "first", "budget_limit": "sum"})
        .drop(columns=["__nama_norm"])
    )
    return df
