import uuid
from datetime import datetime
from connection import get_spreadsheet
import pandas as pd
import re

TRANSACTION_COLUMNS = ["id", "tanggal", "nominal", "tipe", "kategori", "catatan"]


def _normalize_header_cell(value: str) -> str:
    # "Nominal (Rp)" -> "nominal_rp"
    cleaned = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")
    return cleaned


def _has_header_row(first_row: list[str]) -> bool:
    normalized = [_normalize_header_cell(c) for c in first_row]
    expected = [c.lower() for c in TRANSACTION_COLUMNS]
    matches = 0
    for exp in expected:
        if any(cell == exp or cell.startswith(f"{exp}_") or cell.endswith(f"_{exp}") for cell in normalized):
            matches += 1
    # Kalau minimal 3 kolom cocok, anggap itu header row (lebih toleran untuk header yang beda format).
    return matches >= 3


def _normalize_row(row: list[str]) -> list[str]:
    padded = list(row) + [""] * len(TRANSACTION_COLUMNS)
    return padded[: len(TRANSACTION_COLUMNS)]


def _rows_with_header_to_df(values: list[list[str]]) -> pd.DataFrame:
    header = [_normalize_header_cell(c) for c in values[0]]

    index_by_column: dict[str, int] = {}
    for column in TRANSACTION_COLUMNS:
        normalized_column = column.lower()
        for i, cell in enumerate(header):
            if cell == normalized_column or cell.startswith(f"{normalized_column}_") or cell.endswith(f"_{normalized_column}"):
                index_by_column[column] = i
                break

    records: list[dict[str, str]] = []
    for row in values[1:]:
        if not any((c or "").strip() for c in row):
            continue
        record: dict[str, str] = {}
        for column in TRANSACTION_COLUMNS:
            idx = index_by_column.get(column)
            record[column] = (row[idx] if idx is not None and idx < len(row) else "")
        records.append(record)

    return pd.DataFrame(records, columns=TRANSACTION_COLUMNS)


def add_transaction(nominal, tipe, kategori, catatan):
    spreadsheet = get_spreadsheet()
    sheet = spreadsheet.worksheet("transactions")

    tipe_normalized = str(tipe).strip().lower()
    kategori_normalized = str(kategori).strip().lower()
    if tipe_normalized == "pemasukan":
        kategori_normalized = "pemasukan"

    row = [
        str(uuid.uuid4()),           # id unik otomatis
        datetime.now().strftime("%Y-%m-%d"),  # tanggal hari ini
        nominal,
        tipe_normalized,
        kategori_normalized,
        str(catatan or "").strip(),
    ]

    sheet.append_row(row)
    return True

def get_transactions():
    spreadsheet = get_spreadsheet()
    sheet = spreadsheet.worksheet("transactions")

    # Hindari `get_all_records()` karena dia error kalau header row ada duplikat / kolom kosong.
    values = sheet.get_all_values()
    if not values:
        return pd.DataFrame(columns=TRANSACTION_COLUMNS)

    if _has_header_row(values[0]):
        df = _rows_with_header_to_df(values)
    else:
        normalized = [_normalize_row(r) for r in values if any((c or "").strip() for c in r)]
        if not normalized:
            return pd.DataFrame(columns=TRANSACTION_COLUMNS)
        df = pd.DataFrame(normalized, columns=TRANSACTION_COLUMNS)
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
    df["nominal"] = pd.to_numeric(df["nominal"], errors="coerce").fillna(0)
    df["tipe"] = df["tipe"].astype(str).str.strip().str.lower()
    df["kategori"] = df["kategori"].astype(str).str.strip().str.lower()
    return df
