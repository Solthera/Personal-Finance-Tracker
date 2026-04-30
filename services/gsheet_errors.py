from __future__ import annotations

import streamlit as st


def show_spreadsheet_not_found() -> None:
    st.error(
        "Spreadsheet tidak ditemukan / belum di-share ke service account. "
        "Cek `SPREADSHEET_ID`/`SPREADSHEET_NAME` dan pastikan Google Sheet sudah di-share."
    )


def show_worksheet_not_found(sheet_name: str) -> None:
    st.error(f"Worksheet `{sheet_name}` tidak ditemukan. Buat sheet bernama `{sheet_name}` di Google Sheet lo.")

