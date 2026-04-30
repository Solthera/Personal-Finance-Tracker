# Modularisasi `app.py` — Agent-to-Agent Plan

Tujuan dokumen ini adalah memberi rencana eksekusi yang jelas (agent-to-agent) untuk memecah `app.py` yang sudah terlalu panjang menjadi modul-modul yang lebih kecil, mudah dites, dan siap untuk ekspansi fitur (terutama Google OAuth + multi-user).

Dokumen ini **bukan** implementasi; ini adalah checklist + urutan kerja yang sebaiknya diikuti saat membuat branch modularisasi.

---

## 0) Target Outcome (Definition of Done)

Ketika pekerjaan selesai:
- `app.py` hanya berisi:
  - import modul render tab
  - definisi konstanta kecil (atau import dari `constants.py`)
  - wiring `st.tabs(...)` dan pemanggilan `render_*_tab(...)`
- Semua logic UI dan formatting yang besar pindah ke file modul.
- Semua helper umum (format Rupiah, strip token goal_id, styling nominal, perhitungan summary) tidak terduplikasi.
- Tidak ada perubahan perilaku fungsional yang signifikan (kecuali bug fix kecil yang tidak mengubah UX utama).
- Dashboard di `pages/1_Dashboard.py` tetap jalan.

---

## 1) Inventarisasi Logic di `app.py` (Apa yang harus dipisah)

### A. Konstanta & konfigurasi UI
- `EXPENSE_CATEGORIES`
- label tab, judul, teks error umum

### B. Tab Transaksi
- Form tambah transaksi
- Validasi nominal & pesan sukses/error
- Riwayat transaksi:
  - loading df transaksi
  - transform display (tanggal, nominal +/-, strip token `[goal_id:...]`)
  - styling warna berdasarkan `tipe` (pemasukan/pengeluaran/refunds)
  - penambahan kolom `No` mulai dari 1
- Summary:
  - total_masuk
  - total_keluar (net: gross - refunds)
  - saldo (pemasukan - pengeluaran + refunds)

### C. Tab Kategori
- Form tambah kategori (upsert budget)
- Daftar kategori (df_cat)

### D. Tab Goals
- Form tambah goals
- Daftar goals (progress bar + metrics)
- Kelola goals:
  - pilih goal
  - tambah terkumpul:
    - sumber dana: dari pemasukan transaksi vs lainnya
    - pembuatan transaksi goals pengeluaran + token goal_id
    - update terkumpul
  - edit goal
  - hapus goal:
    - refund calculation dari transaksi goals (token/legacy phrase)
    - create transaksi tipe refunds
    - delete row goal

### E. Error handling & messaging
- handler `SpreadsheetNotFound`, `WorksheetNotFound`
- `st.toast`, `st.success`, `st.error`, `st.warning`, `st.stop()`, `st.rerun()`

---

## 2) Struktur Folder yang Direkomendasikan

Buat folder baru:

```
ui/
  __init__.py
  transactions_tab.py
  categories_tab.py
  goals_tab.py
services/
  __init__.py
  formatting.py
  finance_math.py
  gsheet_errors.py
constants.py
```

Catatan:
- `services/*` berisi fungsi non-UI (pure-ish, mudah dites).
- `ui/*` fokus render + wiring event Streamlit.
- `constants.py` menyimpan list kategori dan string yang dipakai lintas modul.

---

## 3) Desain API antar Modul (Agar tidak saling tarik-menari)

### 3.1. `constants.py`
- `EXPENSE_CATEGORIES: list[str]`
- `SYSTEM_CATEGORIES = {"pemasukan", "refunds"}` (opsional)
- Label error standar (opsional)

### 3.2. `services/formatting.py`
Fungsi:
- `strip_goal_id_token(text: str) -> str`
- `format_rupiah(value: float, sign: str|None = None) -> str`
- `format_nominal_signed(tipe: str, nominal: float) -> str`
- `style_nominal_color(tipe: str) -> str` (returns hex)

### 3.3. `services/finance_math.py`
Fungsi:
- `compute_summary(df_transactions) -> dict`
  - returns `total_masuk`, `total_keluar_gross`, `total_refunds`, `total_keluar_net`, `saldo`
- `compute_saldo(df_transactions) -> float` (kalau perlu)

### 3.4. `services/gsheet_errors.py`
Fungsi:
- `handle_gspread_exception(err: Exception, *, context: str) -> None`
  - memetakan `SpreadsheetNotFound/WorksheetNotFound` ke `st.error(...)`
  - (opsional) return boolean success/fail

Catatan:
- Jika modul `services/*` ingin “pure”, jangan import streamlit di situ.
  - Alternatif: `ui/*` yang handle exception dan panggil helper mapping string.
  - Tapi karena Streamlit workflow dominan UI, boleh ada 1 helper UI-level untuk mengurangi repetisi.

### 3.5. `ui/transactions_tab.py`
API:
- `render_transactions_tab() -> None`
  - di dalamnya handle form + history + summary.
  - import `add_transaction`, `get_transactions`

### 3.6. `ui/categories_tab.py`
API:
- `render_categories_tab() -> None`
  - handle form + list.
  - import `add_categories`, `get_categories`

### 3.7. `ui/goals_tab.py`
API:
- `render_goals_tab() -> None`
  - handle form + list + kelola.
  - import `add_goals`, `get_goals`, `update_goal`, `add_to_goal_terkumpul`, `delete_goal`
  - import `add_transaction`, `get_transactions` untuk flow “dari pemasukan” & refund.

---

## 4) Urutan Eksekusi (Step-by-Step)

### Step 1 — Buat struktur file kosong
1. Tambahkan folder `ui/` dan `services/` dengan `__init__.py`.
2. Tambahkan `constants.py` dengan `EXPENSE_CATEGORIES`.
3. Jangan ubah behaviour dulu.

### Step 2 — Pindahkan formatting ke `services/formatting.py`
1. Ambil logic:
   - strip token goal_id dari catatan
   - format nominal `Rp +...` / `Rp -...`
   - mapping warna nominal by tipe (hijau/merah/orange)
2. Pastikan semua pemanggilan di UI memakai helper.

### Step 3 — Pindahkan perhitungan summary ke `services/finance_math.py`
1. Buat fungsi summary yang dipakai di:
   - tab transaksi (cards)
   - dashboard (nanti optional, bisa tetap inline)
2. Pastikan refunds tidak ikut pemasukan.

### Step 4 — Ekstrak Tab Transaksi ke `ui/transactions_tab.py`
1. Copy seluruh blok `with tab_transaksi:` jadi fungsi `render_transactions_tab()`.
2. Pastikan:
   - import `streamlit as st`, `gspread`
   - import `EXPENSE_CATEGORIES` dari `constants`
   - import helper formatting + finance_math
3. Dataframe rendering (style) tetap sama.

### Step 5 — Ekstrak Tab Kategori ke `ui/categories_tab.py`
1. Copy blok `with tab_kategori:` jadi `render_categories_tab()`.
2. Pastikan hasil `add_categories()` (created/updated) men-trigger rerun dan toast.

### Step 6 — Ekstrak Tab Goals ke `ui/goals_tab.py`
1. Copy blok `with tab_goals:` jadi `render_goals_tab()`.
2. Pastikan:
   - flow tambah terkumpul (2 sumber dana) tetap benar.
   - flow hapus goal:
     - refund hanya transaksi terkait goal_id/legacy
     - create transaksi `refunds`
     - delete goal
3. Pastikan display catatan di riwayat transaksi tetap strip token di tab transaksi (bukan di sini).

### Step 7 — Sederhanakan `app.py`
1. `app.py` jadi:
   - set `st.title`
   - `tabs = st.tabs(...)`
   - `with tabs[0]: render_transactions_tab()`, dst.
2. Hapus import yang tidak dipakai.

### Step 8 — Regression check manual
Checklist cepat:
- Bisa tambah transaksi → muncul di history + summary berubah.
- Refunds (hapus goal) → summary & dashboard konsisten.
- Bisa tambah kategori (dua kali sama) → budget diupdate bukan duplikat.
- Bisa tambah goal + tambah terkumpul:
  - sumber dana pemasukan → bikin transaksi pengeluaran goals + update terkumpul
  - sumber dana lainnya → hanya update terkumpul
- Hapus goal → create transaksi refunds + tujuan only that goal.

---

## 5) Poin Kritis / Risiko (Wajib diperhatikan)

1) Streamlit rerun + state:
- Pastikan `st.rerun()` hanya dipanggil saat action sukses (created/updated/delete), bukan saat error.

2) Styling dataframe:
- `.style.apply(...)` harus tetap bekerja setelah refactor.
- Pastikan kolom `No` ditambahkan sebelum `.style` agar style mapping indeks tetap benar.

3) Import cycles:
- Jangan membuat `services/*` import `ui/*`.
- `ui/*` boleh import `services/*` dan `constants.py`.

4) Case normalization:
- `transactions.py` menormalisasi `tipe` & `kategori` ke lowercase.
- `EXPENSE_CATEGORIES` di UI masih Title Case; pastikan saat `add_transaction` tetap ok (backend lowercases).

5) Penghitungan refunds:
- Summary dan dashboard harus konsisten menggunakan rules yang sama.
- Hindari duplikasi rumus; idealnya pakai helper `compute_summary`.

---

## 6) Optional Improvement (Jika ada waktu)

1) Replace repeated error strings:
- Centralize message templates.

2) Add `ui/components.py`:
- `render_gspread_error(err, worksheet_name)`
- `render_summary_cards(summary)`

3) Make dashboard reuse `services/finance_math.py`
- Agar saldo/total konsisten di semua halaman.

---

## 7) Git / Branching Guidance

Nama branch yang disarankan:
- `refactor/modularize-app`

Commits yang disarankan:
1) `chore: add ui/services skeleton`
2) `refactor: extract formatting helpers`
3) `refactor: extract transactions tab`
4) `refactor: extract categories tab`
5) `refactor: extract goals tab`
6) `refactor: simplify app entrypoint`

---

## 8) Acceptance Criteria (Quick)

- `app.py` < ~60–80 lines.
- Tidak ada feature yang hilang.
- Dashboard tetap jalan.
- Semua action utama menghasilkan toast/alert yang konsisten.

