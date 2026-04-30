from __future__ import annotations

import streamlit as st

from constants import EXPENSE_CATEGORIES
from services.finance_math import compute_summary
from services.formatting import format_nominal_signed, strip_goal_id_token, style_nominal_color
from services.gsheet_errors import show_spreadsheet_not_found
from services.gsheet_loaders import load_transactions
from repositories.transactions import add_transaction


def render_transactions_tab() -> None:
    st.subheader("Tambah Transaksi Baru")
    with st.form("form_transaksi"):
        nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000)
        tipe = st.selectbox("Tipe", ["pengeluaran", "pemasukan"])
        if tipe == "pemasukan":
            kategori = st.selectbox("Kategori", ["pemasukan"])
        else:
            kategori = st.selectbox("Kategori", EXPENSE_CATEGORIES)
        catatan = st.text_input("Catatan (opsional)")
        submit_transaksi = st.form_submit_button("Simpan Transaksi")

    if submit_transaksi:
        if nominal == 0:
            st.warning("Nominal tidak boleh 0!")
        else:
            try:
                add_transaction(nominal, tipe, kategori, catatan)
            except gspread.exceptions.SpreadsheetNotFound:
                show_spreadsheet_not_found()
            else:
                st.success("Transaksi berhasil disimpan! ✅")
                st.toast("Transaksi tersimpan.")

    st.divider()
    st.subheader("📋 Riwayat Transaksi")

    df = load_transactions()

    if df is None:
        return
    if df.empty:
        st.info("Belum ada transaksi. Tambahkan transaksi pertama lo!")
        return

    df_display = df.copy()
    df_display["tanggal"] = df_display["tanggal"].dt.strftime("%d %b %Y")
    df_display["catatan"] = df_display["catatan"].astype(str).map(strip_goal_id_token)
    df_display["nominal"] = df_display.apply(
        lambda row: format_nominal_signed(row.get("tipe"), row.get("nominal")), axis=1
    )

    def _style_row(row):
        color = style_nominal_color(row.get("tipe"))
        return ["color: " + color if col == "nominal" else "" for col in row.index]

    st.dataframe(
        df_display.drop(columns=["id"]).style.apply(_style_row, axis=1),
        width="stretch",
    )

    summary = compute_summary(df)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Pemasukan", f"Rp {summary.total_masuk:,.0f}")
    col2.metric("Total Pengeluaran", f"Rp {summary.total_keluar_net:,.0f}")
    col3.metric("Saldo", f"Rp {summary.saldo:,.0f}")
