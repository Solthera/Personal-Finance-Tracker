import uuid
from connection import get_spreadsheet
import pandas as pd

GOALS_COLUMNS = ["id", "nama_target", "nominal_target", "terkumpul", "deadline"]


def _has_header_row(first_row: list[str]) -> bool:
    first = [(c or "").strip().lower() for c in first_row[: len(GOALS_COLUMNS)]]
    expected = [c.lower() for c in GOALS_COLUMNS]
    return first == expected


def _normalize_row(row: list[str]) -> list[str]:
    padded = list(row) + [""] * len(GOALS_COLUMNS)
    return padded[: len(GOALS_COLUMNS)]


def _find_goal_row_number(sheet, goal_id: str) -> int | None:
    values = sheet.get_all_values()
    if not values:
        return None

    has_header = _has_header_row(values[0])
    data_rows = values[1:] if has_header else values
    start_row_number = 2 if has_header else 1

    for offset, row in enumerate(data_rows):
        normalized = _normalize_row(row)
        if normalized[0] == goal_id:
            return start_row_number + offset
    return None


def update_goal(goal_id: str, *, nama_target=None, nominal_target=None, terkumpul=None, deadline=None) -> bool:
    spreadsheet = get_spreadsheet()
    sheet = spreadsheet.worksheet("goals")

    row_number = _find_goal_row_number(sheet, goal_id)
    if row_number is None:
        return False

    current = _normalize_row(sheet.row_values(row_number))
    if nama_target is not None:
        current[1] = str(nama_target).strip()
    if nominal_target is not None:
        current[2] = nominal_target
    if terkumpul is not None:
        current[3] = terkumpul
    if deadline is not None:
        current[4] = str(deadline)

    sheet.update(f"A{row_number}:E{row_number}", [current[:5]])
    return True


def add_to_goal_terkumpul(goal_id: str, amount) -> bool:
    spreadsheet = get_spreadsheet()
    sheet = spreadsheet.worksheet("goals")

    row_number = _find_goal_row_number(sheet, goal_id)
    if row_number is None:
        return False

    current = _normalize_row(sheet.row_values(row_number))
    current_value = pd.to_numeric(current[3], errors="coerce")
    if pd.isna(current_value):
        current_value = 0
    new_value = float(current_value) + float(amount or 0)
    sheet.update_cell(row_number, 4, new_value)  # kolom D = terkumpul
    return True


def delete_goal(goal_id: str) -> bool:
    spreadsheet = get_spreadsheet()
    sheet = spreadsheet.worksheet("goals")

    row_number = _find_goal_row_number(sheet, goal_id)
    if row_number is None:
        return False
    sheet.delete_rows(row_number)
    return True


def add_goals(nama_target, nominal_target, terkumpul, deadline):
    spreadsheet = get_spreadsheet()
    sheet = spreadsheet.worksheet("goals")
    
    row = [
        str(uuid.uuid4()),
        nama_target,
        nominal_target,
        terkumpul,
        str(deadline)   # convert date → string biar bisa masuk GSheet
    ]
    
    sheet.append_row(row)
    return True

def get_goals():
    spreadsheet = get_spreadsheet()
    sheet = spreadsheet.worksheet("goals")
    
    # Hindari `get_all_records()` karena bisa error kalau header row ada kolom kosong/duplikat.
    values = sheet.get_all_values()
    if not values:
        return pd.DataFrame(columns=GOALS_COLUMNS)

    start_index = 1 if _has_header_row(values[0]) else 0
    rows = values[start_index:]
    if not rows:
        return pd.DataFrame(columns=GOALS_COLUMNS)

    normalized = [_normalize_row(r) for r in rows]
    df = pd.DataFrame(normalized, columns=GOALS_COLUMNS)
    df["nominal_target"] = pd.to_numeric(df["nominal_target"], errors="coerce").fillna(0)
    df["terkumpul"] = pd.to_numeric(df["terkumpul"], errors="coerce").fillna(0)
    df["deadline"] = pd.to_datetime(df["deadline"], errors="coerce")
    return df
