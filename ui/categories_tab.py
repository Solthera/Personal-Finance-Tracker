from __future__ import annotations

import streamlit as st

from repositories.categories import add_categories
from constants import EXPENSE_CATEGORIES
from services.gsheet_errors import show_spreadsheet_not_found
from services.gsheet_loaders import load_categories


def render_categories_tab() -> None:
    st.subheader("Tambah Kategori")

    with st.form("form_categories"):
        nama_kategori = st.selectbox("Nama Kategori", EXPENSE_CATEGORIES)
        budget_limit = st.number_input("Budget Limit (Rp)", min_value=0, step=1000)
        submit_kategori = st.form_submit_button("Simpan Kategori")

    if submit_kategori:
        if not nama_kategori.strip():
            st.warning("Nama kategori tidak boleh kosong!")
        else:
            try:
                result = add_categories(nama_kategori.strip(), budget_limit)
            except gspread.exceptions.SpreadsheetNotFound:
                show_spreadsheet_not_found()
            else:
                if result == "updated":
                    st.success("Kategori sudah ada — budget berhasil ditambahkan ✅")
                    st.toast("Budget kategori diupdate.")
                else:
                    st.success("Kategori berhasil disimpan! ✅")
                    st.toast("Kategori tersimpan.")
                st.rerun()

    st.divider()
    st.subheader("📋 Daftar Kategori")

    df_cat = load_categories()

    if df_cat is None:
        return
    if df_cat.empty:
        st.info("Belum ada kategori.")
        return

    df_cat_display = df_cat.copy()
    df_cat_display["budget_limit"] = df_cat_display["budget_limit"].apply(lambda x: f"Rp {x:,.0f}")
    st.dataframe(df_cat_display.drop(columns=["id"]), width="stretch")
