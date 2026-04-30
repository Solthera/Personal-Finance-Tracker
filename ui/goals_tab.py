from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import gspread

from repositories.goals import add_goals, add_to_goal_terkumpul, delete_goal, update_goal
from services.finance_math import compute_summary
from services.gsheet_errors import show_spreadsheet_not_found
from services.gsheet_loaders import load_goals, load_transactions
from repositories.transactions import add_transaction


def render_goals_tab() -> None:
    st.subheader("Tambah Goals")
    with st.form("form_goals"):
        nama_goal = st.text_input("Nama Target")
        nominal_target = st.number_input("Nominal Target (Rp)", min_value=0, step=1000)
        terkumpul = st.number_input("Terkumpul Saat Ini (Rp)", min_value=0, step=1000)
        deadline = st.date_input("Deadline")
        submit_goals = st.form_submit_button("Simpan Goals")

    if submit_goals:
        if not nama_goal.strip():
            st.warning("Nama target tidak boleh kosong!")
        elif nominal_target == 0:
            st.warning("Nominal target tidak boleh 0!")
        else:
            try:
                add_goals(nama_goal.strip(), nominal_target, terkumpul, deadline)
            except gspread.exceptions.SpreadsheetNotFound:
                show_spreadsheet_not_found()
            else:
                st.success("Goals berhasil disimpan! ✅")
                st.toast("Goals tersimpan.")

    st.divider()
    st.subheader("🎯 Daftar Goals")

    df_goals = load_goals()

    if df_goals is None:
        return
    if df_goals.empty:
        st.info("Belum ada goals.")
        return

    for _, row in df_goals.iterrows():
        nominal_target_row = float(row.get("nominal_target") or 0)
        terkumpul_row = float(row.get("terkumpul") or 0)
        progress = (terkumpul_row / nominal_target_row) if nominal_target_row > 0 else 0

        st.markdown(f"**{row.get('nama_target', '')}**")
        st.progress(min(progress, 1.0))

        deadline_value = row.get("deadline")
        deadline_text = "-"
        try:
            deadline_text = deadline_value.strftime("%d %b %Y")
        except Exception:
            pass

        col1, col2, col3 = st.columns(3)
        col1.metric("Target", f"Rp {nominal_target_row:,.0f}")
        col2.metric("Terkumpul", f"Rp {terkumpul_row:,.0f}")
        col3.metric("Deadline", deadline_text)

        st.divider()

    st.subheader("🛠️ Kelola Goals")
    options: dict[str, str] = {}
    for _, r in df_goals.iterrows():
        goal_id = str(r.get("id", "") or "")
        short_id = goal_id[:8] if goal_id else "unknown"
        label = f"{r.get('nama_target', '')} (Rp {float(r.get('nominal_target') or 0):,.0f}) — {short_id}"
        options[label] = goal_id
    selected_label = st.selectbox("Pilih Goal", list(options.keys()))
    selected_goal_id = options.get(selected_label, "")

    selected_goal = df_goals[df_goals["id"] == selected_goal_id].iloc[0]
    action = st.radio("Aksi", ["Tambah Terkumpul", "Edit", "Hapus"], horizontal=True)

    if action == "Tambah Terkumpul":
        with st.form("form_goals_add_amount"):
            amount = st.number_input("Tambah Nominal (Rp)", min_value=0, step=1000)
            sumber_dana = st.selectbox("Sumber Dana", ["Dari pemasukan transaksi", "Lainnya (isi catatan)"])
            catatan_sumber = ""
            if sumber_dana.startswith("Lainnya"):
                catatan_sumber = st.text_input("Catatan Sumber Dana")
            submit_amount = st.form_submit_button("Tambah")

        if submit_amount:
            if amount <= 0:
                st.warning("Nominal tambah harus > 0.")
            elif sumber_dana.startswith("Lainnya") and not catatan_sumber.strip():
                st.warning("Kalau sumber dana 'Lainnya', catatan wajib diisi.")
            else:
                if sumber_dana.startswith("Dari pemasukan"):
                    df_tx = load_transactions()
                    if df_tx is None:
                        st.error("Gagal potong saldo: data transaksi tidak bisa dibaca.")
                        st.stop()

                    saldo = compute_summary(df_tx).saldo
                    if saldo < amount:
                        st.error(f"Saldo tidak cukup. Saldo sekarang: Rp {saldo:,.0f}")
                        st.stop()

                    nama_target = str(selected_goal.get("nama_target") or "").strip()
                    try:
                        add_transaction(
                            amount,
                            "pengeluaran",
                            "goals",
                            f'[goal_id:{selected_goal_id}] Menyisihkan dana untuk "{nama_target}"',
                        )
                    except gspread.exceptions.SpreadsheetNotFound:
                        st.error("Gagal menyimpan transaksi pengeluaran: spreadsheet tidak ditemukan / belum di-share.")
                        st.stop()
                    except gspread.exceptions.WorksheetNotFound:
                        st.error("Gagal menyimpan transaksi pengeluaran: worksheet `transactions` tidak ditemukan.")
                        st.stop()

                    try:
                        ok = add_to_goal_terkumpul(selected_goal_id, amount)
                    except gspread.exceptions.SpreadsheetNotFound:
                        st.error("Gagal update goals: spreadsheet tidak ditemukan / belum di-share.")
                        st.stop()
                    except gspread.exceptions.WorksheetNotFound:
                        st.error(
                            "Worksheet `goals` tidak ditemukan. Buat sheet bernama `goals` di Google Sheet lo."
                        )
                        st.stop()

                    if not ok:
                        st.error("Goal tidak ditemukan di worksheet.")
                    else:
                        st.success("Terkumpul berhasil ditambah ✅")
                        st.toast(f'Potong saldo: Rp {amount:,.0f} → transaksi "pengeluaran" kategori "goals".')
                        st.toast("Goals berhasil diperbarui.")
                        st.rerun()
                else:
                    try:
                        ok = add_to_goal_terkumpul(selected_goal_id, amount)
                    except gspread.exceptions.SpreadsheetNotFound:
                        st.error("Spreadsheet tidak ditemukan / belum di-share ke service account.")
                        st.stop()
                    except gspread.exceptions.WorksheetNotFound:
                        st.error("Worksheet `goals` tidak ditemukan. Buat sheet bernama `goals` di Google Sheet lo.")
                        st.stop()

                    if not ok:
                        st.error("Goal tidak ditemukan di worksheet.")
                    else:
                        st.success("Terkumpul berhasil ditambah ✅")
                        st.toast(f"Sumber dana: {catatan_sumber.strip()}")
                        st.toast("Goals berhasil diperbarui.")
                        st.rerun()

    elif action == "Edit":
        existing_deadline = selected_goal.get("deadline")
        if pd.isna(existing_deadline):
            existing_deadline_date = date.today()
        else:
            existing_deadline_date = existing_deadline.date()

        with st.form("form_goals_edit"):
            new_nama = st.text_input("Nama Target", value=str(selected_goal.get("nama_target") or ""))
            new_nominal_target = st.number_input(
                "Nominal Target (Rp)",
                min_value=0,
                step=1000,
                value=int(float(selected_goal.get("nominal_target") or 0)),
            )
            new_terkumpul = st.number_input(
                "Terkumpul (Rp)",
                min_value=0,
                step=1000,
                value=int(float(selected_goal.get("terkumpul") or 0)),
            )
            new_deadline = st.date_input("Deadline", value=existing_deadline_date)
            submit_edit = st.form_submit_button("Simpan Perubahan")

        if submit_edit:
            if not new_nama.strip():
                st.warning("Nama target tidak boleh kosong!")
            elif new_nominal_target == 0:
                st.warning("Nominal target tidak boleh 0!")
            else:
                try:
                    ok = update_goal(
                        selected_goal_id,
                        nama_target=new_nama.strip(),
                        nominal_target=new_nominal_target,
                        terkumpul=new_terkumpul,
                        deadline=new_deadline,
                    )
                except gspread.exceptions.SpreadsheetNotFound:
                    st.error("Spreadsheet tidak ditemukan / belum di-share ke service account.")
                except gspread.exceptions.WorksheetNotFound:
                    st.error("Worksheet `goals` tidak ditemukan. Buat sheet bernama `goals` di Google Sheet lo.")
                else:
                    if not ok:
                        st.error("Goal tidak ditemukan di worksheet.")
                    else:
                        st.success("Goal berhasil diupdate ✅")
                        st.toast("Goals diupdate.")
                        st.rerun()

    else:  # Hapus
        st.warning("Aksi ini akan menghapus goal dari Google Sheet.")
        confirm = st.checkbox("Saya yakin ingin menghapus goal ini.")
        if st.button("Hapus Goal", disabled=not confirm):
            refund_amount = 0.0
            goal_name = str(selected_goal.get("nama_target") or "").strip()
            df_tx = load_transactions()

            if df_tx is not None and not df_tx.empty:
                token = f"[goal_id:{selected_goal_id}]"
                catatan_lower = df_tx["catatan"].astype(str).str.lower()
                token_mask = catatan_lower.str.contains(token.lower(), na=False, regex=False)
                legacy_phrase = f'menyisihkan dana untuk "{goal_name.lower()}"'
                legacy_mask = catatan_lower.str.contains(legacy_phrase, na=False, regex=False)
                mask = (
                    (df_tx["tipe"] == "pengeluaran")
                    & (df_tx["kategori"] == "goals")
                    & (token_mask | legacy_mask)
                )
                refund_amount = float(df_tx.loc[mask, "nominal"].sum() or 0)

            try:
                ok = delete_goal(selected_goal_id)
            except gspread.exceptions.SpreadsheetNotFound:
                st.error("Spreadsheet tidak ditemukan / belum di-share ke service account.")
            except gspread.exceptions.WorksheetNotFound:
                st.error("Worksheet `goals` tidak ditemukan. Buat sheet bernama `goals` di Google Sheet lo.")
            else:
                if not ok:
                    st.error("Goal tidak ditemukan di worksheet.")
                else:
                    if refund_amount > 0:
                        try:
                            add_transaction(
                                refund_amount,
                                "refunds",
                                "refunds",
                                f'pembatalan pembelian "{goal_name}" [goal_id:{selected_goal_id}]',
                            )
                        except gspread.exceptions.SpreadsheetNotFound:
                            st.error(
                                "Goals sudah terhapus, tapi gagal mengembalikan dana (spreadsheet tidak ditemukan). "
                                f"Tambahkan manual pemasukan Rp {refund_amount:,.0f}."
                            )
                        except gspread.exceptions.WorksheetNotFound:
                            st.error(
                                "Goals sudah terhapus, tapi gagal mengembalikan dana (worksheet transactions tidak ada). "
                                f"Tambahkan manual pemasukan Rp {refund_amount:,.0f}."
                            )
                        else:
                            st.toast(f"Dana dikembalikan: Rp {refund_amount:,.0f}")
                    else:
                        st.toast("Tidak ada dana transaksi untuk dikembalikan.")

                    st.success("Goal berhasil dihapus ✅")
                    st.toast("Goals dihapus.")
                    st.rerun()
