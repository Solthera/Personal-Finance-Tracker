import streamlit as st
import gspread
import pandas as pd
from datetime import date
from transactions import add_transaction, get_transactions
from categories import add_categories, get_categories
from goals import add_goals, get_goals, update_goal, add_to_goal_terkumpul, delete_goal

st.title("💰 Personal Finance Tracker")

tab_transaksi, tab_kategori, tab_goals = st.tabs(["Transaksi", "Kategori", "Goals"])

with tab_transaksi:
    st.subheader("Tambah Transaksi Baru")
    with st.form("form_transaksi"):
        nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000)
        tipe = st.selectbox("Tipe", ["pengeluaran", "pemasukan"])
        if tipe == "pemasukan":
            kategori = st.selectbox("Kategori", ["pemasukan"])
        else:
            kategori = st.selectbox(
                "Kategori",
                ["Makan", "Transport", "Hiburan", "Belanja", "Tagihan", "Investasi", "Goals", "Lainnya"],
            )
        catatan = st.text_input("Catatan (opsional)")
        submit_transaksi = st.form_submit_button("Simpan Transaksi")

    if submit_transaksi:
        if nominal == 0:
            st.warning("Nominal tidak boleh 0!")
        else:
            try:
                add_transaction(nominal, tipe, kategori, catatan)
            except gspread.exceptions.SpreadsheetNotFound:
                st.error(
                    "Spreadsheet tidak ditemukan / belum di-share ke service account. "
                    "Cek `SPREADSHEET_ID`/`SPREADSHEET_NAME` dan pastikan Google Sheet sudah di-share."
                )
            else:
                st.success("Transaksi berhasil disimpan! ✅")
                st.toast("Transaksi tersimpan.")

    st.divider()
    st.subheader("📋 Riwayat Transaksi")

    try:
        df = get_transactions()
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(
            "Spreadsheet tidak ditemukan / belum di-share ke service account. "
            "Cek `SPREADSHEET_ID`/`SPREADSHEET_NAME` dan pastikan Google Sheet sudah di-share."
        )
        df = None
    except gspread.exceptions.WorksheetNotFound:
        st.error("Worksheet `transactions` tidak ditemukan. Buat sheet bernama `transactions` di Google Sheet lo.")
        df = None

    if df is None:
        pass
    elif df.empty:
        st.info("Belum ada transaksi. Tambahkan transaksi pertama lo!")
    else:
        df_display = df.copy()
        df_display["tanggal"] = df_display["tanggal"].dt.strftime("%d %b %Y")
        df_display["catatan"] = (
            df_display["catatan"]
            .astype(str)
            .str.replace(r"\[goal_id:[^\]]+\]\s*", "", regex=True)
            .str.strip()
        )

        def _format_nominal(row):
            value = float(row.get("nominal") or 0)
            tipe_row = str(row.get("tipe") or "").lower()
            if tipe_row == "pengeluaran":
                return f"Rp -{value:,.0f}"
            return f"Rp +{value:,.0f}"

        df_display["nominal"] = df_display.apply(_format_nominal, axis=1)

        def _style_row(row):
            tipe_row = str(row.get("tipe") or "").lower()
            if tipe_row == "pemasukan":
                color = "#2ecc71"
            elif tipe_row == "refunds":
                color = "#f39c12"
            else:
                color = "#e74c3c"
            return ["color: " + color if col == "nominal" else "" for col in row.index]

        st.dataframe(
            df_display.drop(columns=["id"]).style.apply(_style_row, axis=1),
            use_container_width=True,
        )

        total_masuk = df[df["tipe"] == "pemasukan"]["nominal"].sum()
        total_refunds = df[df["tipe"] == "refunds"]["nominal"].sum()
        total_keluar_gross = df[df["tipe"] == "pengeluaran"]["nominal"].sum()
        total_keluar = total_keluar_gross - total_refunds
        saldo = total_masuk - total_keluar_gross + total_refunds

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Pemasukan", f"Rp {total_masuk:,.0f}")
        col2.metric("Total Pengeluaran", f"Rp {total_keluar:,.0f}")
        col3.metric("Saldo", f"Rp {saldo:,.0f}")

with tab_kategori:
    st.subheader("Tambah Kategori")
    with st.form("form_categories"):
        nama_kategori = st.text_input("Nama Kategori")
        budget_limit = st.number_input("Budget Limit (Rp)", min_value=0, step=1000)
        submit_kategori = st.form_submit_button("Simpan Kategori")

    if submit_kategori:
        if not nama_kategori.strip():
            st.warning("Nama kategori tidak boleh kosong!")
        else:
            try:
                add_categories(nama_kategori.strip(), budget_limit)
            except gspread.exceptions.SpreadsheetNotFound:
                st.error(
                    "Spreadsheet tidak ditemukan / belum di-share ke service account. "
                    "Cek `SPREADSHEET_ID`/`SPREADSHEET_NAME` dan pastikan Google Sheet sudah di-share."
                )
            else:
                st.success("Kategori berhasil disimpan! ✅")
                st.toast("Kategori tersimpan.")

    st.divider()
    st.subheader("📋 Daftar Kategori")

    try:
        df_cat = get_categories()
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(
            "Spreadsheet tidak ditemukan / belum di-share ke service account. "
            "Cek `SPREADSHEET_ID`/`SPREADSHEET_NAME` dan pastikan Google Sheet sudah di-share."
        )
        df_cat = None
    except gspread.exceptions.WorksheetNotFound:
        st.error("Worksheet `categories` tidak ditemukan. Buat sheet bernama `categories` di Google Sheet lo.")
        df_cat = None

    if df_cat is None:
        pass
    elif df_cat.empty:
        st.info("Belum ada kategori.")
    else:
        df_cat_display = df_cat.copy()
        df_cat_display["budget_limit"] = df_cat_display["budget_limit"].apply(lambda x: f"Rp {x:,.0f}")
        st.dataframe(df_cat_display.drop(columns=["id"]), use_container_width=True)

with tab_goals:
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
                st.error(
                    "Spreadsheet tidak ditemukan / belum di-share ke service account. "
                    "Cek `SPREADSHEET_ID`/`SPREADSHEET_NAME` dan pastikan Google Sheet sudah di-share."
                )
            else:
                st.success("Goals berhasil disimpan! ✅")
                st.toast("Goals tersimpan.")

    st.divider()
    st.subheader("🎯 Daftar Goals")

    try:
        df_goals = get_goals()
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(
            "Spreadsheet tidak ditemukan / belum di-share ke service account. "
            "Cek `SPREADSHEET_ID`/`SPREADSHEET_NAME` dan pastikan Google Sheet sudah di-share."
        )
        df_goals = None
    except gspread.exceptions.WorksheetNotFound:
        st.error("Worksheet `goals` tidak ditemukan. Buat sheet bernama `goals` di Google Sheet lo.")
        df_goals = None

    if df_goals is None:
        pass
    elif df_goals.empty:
        st.info("Belum ada goals.")
    else:
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
        options = {}
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
                        try:
                            df_tx = get_transactions()
                        except gspread.exceptions.SpreadsheetNotFound:
                            st.error("Gagal potong saldo: spreadsheet transactions tidak ditemukan / belum di-share.")
                            st.stop()
                        except gspread.exceptions.WorksheetNotFound:
                            st.error("Gagal potong saldo: worksheet `transactions` tidak ditemukan.")
                            st.stop()

                        total_masuk = df_tx[df_tx["tipe"] == "pemasukan"]["nominal"].sum()
                        total_refunds = df_tx[df_tx["tipe"] == "refunds"]["nominal"].sum()
                        total_keluar_gross = df_tx[df_tx["tipe"] == "pengeluaran"]["nominal"].sum()
                        saldo = total_masuk - total_keluar_gross + total_refunds

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
                            st.error("Worksheet `goals` tidak ditemukan. Buat sheet bernama `goals` di Google Sheet lo.")
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
                try:
                    df_tx = get_transactions()
                except Exception:
                    df_tx = None

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
