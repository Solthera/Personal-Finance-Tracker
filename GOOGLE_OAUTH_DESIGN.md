# Perancangan & Implementasi Google OAuth (Multi-User, Data Terpisah per User)
Project: PersonalFi / Personal Finance Tracker (Streamlit + Google Sheets)

Dokumen ini menjelaskan rancangan dan rencana implementasi Google OAuth agar aplikasi bisa dipakai banyak orang tanpa mencampur data, dengan storage utama tetap Google Sheets **milik masing-masing user** (zero-cost DB hosting).

---

## 1) Problem Statement
Saat ini aplikasi memakai 1 spreadsheet (punya developer) yang diakses melalui service account. Jika app dibuat publik, semua user akan menulis ke sheet yang sama → data developer bercampur dan berubah.

Target solusi:
- User tinggal “pakai” app (minim teknis).
- Data tiap user **terpisah**.
- Tidak perlu biaya hosting database eksternal.

---

## 2) Solusi yang Dipilih (High-Level)
Gunakan **Google OAuth** (Sign in with Google) sehingga:
- App mengakses Google Drive/Sheets menggunakan token user.
- App membuat/membuka spreadsheet **khusus user** di Drive user.
- Semua operasi CRUD (transactions, categories, goals) dilakukan pada spreadsheet user tersebut.

Dengan model ini:
- Tidak perlu service account untuk akses sheet user.
- Tidak perlu database eksternal untuk isolasi data.
- User cukup login Google + approve permissions.

---

## 3) Konsep Multi-Tenant Tanpa Database
Karena tidak ingin DB eksternal, mapping “user → spreadsheet” ditangani lewat Drive user.

Strategi mapping yang direkomendasikan:
1) Cari spreadsheet dengan nama tetap (mis. `Personal Finance Tracker`) di Drive user.
2) Jika tidak ada → buat spreadsheet baru + set worksheet + header.
3) Simpan “identitas” spreadsheet di metadata Drive agar pencarian stabil:
   - Alternatif A (lebih rapi): set `appProperties` pada file Drive (Drive API) seperti:
     - `appProperties.codename = "PersonalFi"`
     - `appProperties.schema_version = "1"`
   - Alternatif B (lebih simpel): nama file + struktur sheet.

Catatan:
- Alternatif A butuh Drive API scope dan pemakaian Drive API untuk set/get `appProperties`.
- Alternatif B paling gampang, tapi risiko bentrok kalau user rename file.

Rekomendasi: mulai dari **Alternatif B** (name-based) agar cepat, lalu upgrade ke appProperties jika diperlukan.

---

## 4) UX Flow (User Side)
1) User buka app Streamlit.
2) App menampilkan tombol “Login dengan Google”.
3) User login → redirect balik ke app.
4) App mengecek spreadsheet user:
   - jika ada → buka.
   - jika belum → buat otomatis dari template/struktur default.
5) UI normal (tab Transaksi/Kategori/Goals/Dashboard) berjalan dengan data user.

Tambahan UX:
- Tombol “Logout”.
- Tombol “Ganti Spreadsheet” (opsional advanced).
- Info kecil: spreadsheet yang dipakai (nama atau link).

---

## 5) Google Cloud Setup (Developer Tasks)
Di Google Cloud Console (GCP):
1) Buat project (atau pakai yang sudah ada).
2) Enable APIs:
   - Google Sheets API
   - Google Drive API (dibutuhkan jika mau create file / search file / appProperties)
3) OAuth Consent Screen:
   - App name, support email, developer contact.
   - Tambahkan scope minimal.
   - Jika app publik: atur status publishing (Testing/Production) + verifikasi jika scope sensitif.
4) Buat OAuth Client ID:
   - Tipe: Web application
   - Authorized redirect URIs: redirect URL milik Streamlit Cloud.

Redirect URI di Streamlit Cloud biasanya seperti:
- `https://<your-app-name>.streamlit.app/`
atau endpoint khusus callback (lebih rapi):
- `https://<your-app-name>.streamlit.app/?oauth_callback=1`
(Kita akan handle query params di Streamlit.)

---

## 6) Scope Permissions (Minimal)
Tujuan: bisa create & read/write spreadsheet user, dan list/search file.

Pilihan scope (urutan dari paling “aman” ke paling “powerful”):

### Opsi 1 (lebih sempit, recommended jika implementasi bisa):
- Sheets read/write:
  - `https://www.googleapis.com/auth/spreadsheets`
- Drive “file per app”:
  - `https://www.googleapis.com/auth/drive.file`

`drive.file` memungkinkan app membuat dan mengakses file yang dibuat/dibuka oleh app, tapi listing/search bisa terbatas tergantung implementasi. Biasanya cukup jika app membuat spreadsheet sendiri.

### Opsi 2 (lebih luas, lebih mudah untuk search):
- `https://www.googleapis.com/auth/drive`
(Full Drive access; bisa memicu trust issue untuk user.)

Rekomendasi: pakai **drive.file + spreadsheets** dan biarkan app membuat spreadsheet sendiri untuk user pertama kali, agar tidak perlu akses penuh Drive.

---

## 7) Token Model & Keamanan
Google OAuth menghasilkan:
- `access_token` (umur pendek)
- `refresh_token` (untuk mint access token baru tanpa login ulang; biasanya hanya diberikan saat first consent dan `access_type=offline` + `prompt=consent`)

Di Streamlit:
- Simpan token di `st.session_state` untuk session berjalan.
- Untuk persist antar session (user balik besok), ada beberapa opsi:
  - Opsi A (tanpa storage): user login ulang (paling simple, UX kurang).
  - Opsi B (cookie + signed token) – butuh komponen tambahan.
  - Opsi C (DB) – tidak mau.

Rekomendasi fase 1:
- Simpan token di session; user login ulang kalau session habis.
- Tambahkan handling refresh token kalau ada, untuk mengurangi login ulang selama session.

Catatan keamanan:
- Jangan pernah log token ke output.
- Jangan simpan token ke repo.
- Set `client_secret` di Streamlit Secrets.

---

## 8) Perubahan Struktur Kode (Refactor Plan)
Saat ini ada `connection.py` berbasis service account.

Kita akan tambahkan layer baru:

### File/Module Baru
1) `auth_google.py`
   - Build authorization URL
   - Handle callback query params (`code`)
   - Exchange `code` → token
   - Refresh token
   - Get user info (opsional) untuk display

2) `google_clients.py`
   - `get_sheets_client(access_token)` atau pakai `googleapiclient`
   - `get_drive_client(access_token)` (opsional tergantung scope)

3) `user_storage.py` (konsep “storage backend”)
   - `get_or_create_user_spreadsheet(...)`
   - `ensure_schema(spreadsheet)` → create worksheets & header

### Modifikasi File Existing
- `connection.py`
  - Diubah jadi “router”:
    - mode dev (service account) untuk local saja (opsional)
    - mode prod (OAuth) untuk multi-user
  - Atau dipisah: `connection_sa.py` dan `connection_oauth.py`

- `transactions.py`, `categories.py`, `goals.py`
  - Ubah signature fungsi: jangan panggil `get_spreadsheet()` global tanpa konteks user.
  - Introduce dependency injection:
    - `add_transaction(spreadsheet, ...)`
    - `get_transactions(spreadsheet)`
  - Atau `get_spreadsheet_for_current_user()` yang sudah “per-user” dari session.

Rekomendasi: langkah bertahap:
1) Buat `get_spreadsheet_for_user()` yang memakai token dari session.
2) Biarkan API modul tetap sama dulu (minim perubahan).
3) Setelah stabil, baru DI/refactor lebih bersih.

---

## 9) Schema Spreadsheet User
Workbook `Personal Finance Tracker` berisi worksheets:

### `transactions`
Header:
- `id`, `tanggal`, `nominal`, `tipe`, `kategori`, `catatan`

### `categories`
Header:
- `id`, `nama`, `budget_limit`

### `goals`
Header:
- `id`, `nama_target`, `nominal_target`, `terkumpul`, `deadline`

Saat “create spreadsheet baru”, app:
- Create 3 worksheet jika belum ada.
- Set row header jika kosong.
- (Opsional) freeze header row.

---

## 10) Implementasi OAuth di Streamlit (Detail)
Streamlit berjalan “rerun” tiap interaksi, jadi flow OAuth perlu aman dari rerun.

### State yang dibutuhkan di `st.session_state`
- `oauth_state` (CSRF protection)
- `oauth_token` (dict: access_token, refresh_token, expiry)
- `user_email` / `user_id` (opsional)
- `spreadsheet_id` (hasil get_or_create per user)

### OAuth Steps
1) Generate login URL:
   - `state = secrets.token_urlsafe(32)`
   - simpan ke `session_state.oauth_state`
   - build URL dengan params:
     - `client_id`
     - `redirect_uri`
     - `response_type=code`
     - `scope=...`
     - `access_type=offline`
     - `prompt=consent` (supaya refresh_token keluar)
     - `state=...`

2) Callback handling:
   - baca query params `code`, `state`
   - validasi state
   - POST ke token endpoint untuk exchange
   - simpan token ke session_state
   - bersihkan query params (opsional) agar tidak re-exchange tiap rerun

3) Token refresh:
   - jika token expired dan ada refresh_token:
     - refresh otomatis sebelum call API

### Library pilihan
- `google-auth` + `google-auth-oauthlib` + `google-api-python-client`
atau
- request manual (requests) ke token endpoint + `gspread` dengan authorized session

Karena project sudah memakai `gspread`, opsi praktis:
- Gunakan `google.oauth2.credentials.Credentials` dari `google-auth` untuk OAuth
- Buat client gspread dari credential OAuth

---

## 11) Drive/Sheets Ops (Find/Create Spreadsheet)
Pseudo-flow:
1) `find_spreadsheet()`
   - kalau pakai name-based: query Drive `name="Personal Finance Tracker" and mimeType="application/vnd.google-apps.spreadsheet" and trashed=false`
2) jika tidak ada:
   - create spreadsheet via Sheets API (`spreadsheets.create`) atau Drive API create
   - set worksheets & header

Jika memakai `drive.file`, search mungkin terbatas. Strategi yang biasanya aman:
- Selalu create spreadsheet oleh app → app pasti bisa akses file itu.
- Simpan spreadsheet id di session.
- Untuk “recall” tanpa DB, bisa:
  - tetap search (kalau scope memungkinkan), atau
  - simpan `spreadsheetId` di file khusus (mis. doc kecil) yang dibuat app (masih di Drive user).

---

## 12) Perubahan Logika Finansial (Catatan)
Karena sudah ada tipe khusus `refunds`:
- Summary:
  - `total pemasukan` = sum(tipe==pemasukan)
  - `total refunds` = sum(tipe==refunds)
  - `total pengeluaran net` = sum(pengeluaran) - sum(refunds)
  - `saldo` = pemasukan - pengeluaran + refunds
- Dashboard budget vs aktual:
  - “aktual” bulan ini untuk kategori `goals` dikurangi refunds bulan ini.

Semua ini harus tetap konsisten setelah OAuth; cukup pastikan sheet user punya data valid dan parse tanggal/nominal robust.

---

## 13) Deployment di Streamlit Cloud (Secrets)
Di Streamlit Cloud → Settings → Secrets (TOML), simpan:
- `GOOGLE_OAUTH_CLIENT_ID = "...."`
- `GOOGLE_OAUTH_CLIENT_SECRET = "...."`
- `GOOGLE_OAUTH_REDIRECT_URI = "https://<app>.streamlit.app/"`
- (opsional) `GOOGLE_OAUTH_SCOPES = "..."` (atau hardcode list)

Untuk dev local:
- bisa pakai `.env` atau `credentials.json` service account (mode dev).

---

## 14) Migrasi dari Service Account (Strategi)
Phase 1 (quick win):
- Tambah OAuth login untuk user.
- Developer masih bisa pakai service account lokal untuk testing pribadi.

Phase 2 (clean):
- Default selalu OAuth.
- Service account path hanya untuk maintenance/internal.

---

## 15) Testing Checklist
Functional:
- Login Google sukses.
- User A create spreadsheet → worksheets dibuat.
- User B login → spreadsheet berbeda.
- CRUD transaksi/categories/goals jalan pada spreadsheet masing-masing.
- Dashboard aman (filter tanggal).

Edge cases:
- Spreadsheet user terhapus/rename.
- Token expired → refresh.
- User revoke access → app minta login ulang.
- Worksheet hilang → app recreate (atau show error).

Security:
- `state` validation bekerja.
- Token tidak tampil di logs/UI.

---

## 16) Estimasi Work & Milestones
1) Setup GCP OAuth + secrets (0.5–1 hari)
2) Implement login flow + token store (1–2 hari)
3) Implement find/create spreadsheet per user (1–2 hari)
4) Integrasi ke `get_spreadsheet()` dan modul existing (1–2 hari)
5) QA + edge cases + polish UX (1–2 hari)

---

## 17) Catatan Penting
- Jika app publik dan memakai scope sensitif/luas, Google bisa meminta verifikasi.
- Minimalkan scope untuk menjaga trust user.
- Untuk awal, bisa publish dalam mode “Testing” + whitelist test users (Google Cloud).

