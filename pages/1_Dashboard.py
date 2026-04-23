import streamlit as st
import plotly.express as px
import gspread
import pandas as pd
from transactions import get_transactions
from categories import get_categories
from insight import generate_insights

st.title("📊 Dashboard")
st.divider()

try:
    df = get_transactions()
except gspread.exceptions.SpreadsheetNotFound:
    st.error(
        "Spreadsheet tidak ditemukan / belum di-share ke service account. "
        "Cek `SPREADSHEET_ID`/`SPREADSHEET_NAME` dan pastikan Google Sheet sudah di-share."
    )
    st.stop()
except gspread.exceptions.WorksheetNotFound:
    st.error("Worksheet `transactions` tidak ditemukan. Buat sheet bernama `transactions` di Google Sheet lo.")
    st.stop()

if df.empty:
    st.warning("Belum ada data transaksi. Tambahkan dulu di halaman utama!")
    st.stop()

# ── Summary Cards ──────────────────────────────
total_masuk = df[df["tipe"] == "pemasukan"]["nominal"].sum()
total_refunds = df[df["tipe"] == "refunds"]["nominal"].sum()
total_keluar_gross = df[df["tipe"] == "pengeluaran"]["nominal"].sum()
total_keluar = total_keluar_gross - total_refunds
saldo = total_masuk - total_keluar_gross + total_refunds

col1, col2, col3 = st.columns(3)
col1.metric("💵 Total Pemasukan", f"Rp {total_masuk:,.0f}")
col2.metric("💸 Total Pengeluaran", f"Rp {total_keluar:,.0f}")
col3.metric("🏦 Saldo", f"Rp {saldo:,.0f}", 
            delta=f"Rp {saldo:,.0f}",
            delta_color="normal")

st.divider()

# ── Chart 1: Pengeluaran per Kategori ──────────
st.subheader("🍩 Pengeluaran per Kategori")

df_keluar = df[df["tipe"] == "pengeluaran"]

if df_keluar.empty:
    st.info("Belum ada data pengeluaran.")
else:
    pie_data = df_keluar.groupby("kategori")["nominal"].sum().reset_index()
    fig_pie = px.pie(
        pie_data,
        names="kategori",
        values="nominal",
        hole=0.4
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# ── Chart 2: Tren Pemasukan vs Pengeluaran ──────
st.subheader("📈 Tren Bulanan")

df["bulan"] = df["tanggal"].dt.to_period("M").astype(str)
tren = df.groupby(["bulan", "tipe"])["nominal"].sum().reset_index()

fig_bar = px.bar(
    tren,
    x="bulan",
    y="nominal",
    color="tipe",
    barmode="group",
    color_discrete_map={
        "pemasukan": "#2ecc71",
        "pengeluaran": "#e74c3c",
        "refunds": "#f39c12",
    },
    labels={"nominal": "Nominal (Rp)", "bulan": "Bulan"}
)
st.plotly_chart(fig_bar, use_container_width=True)

# ── Chart 3: Budget vs Aktual ───────────────────
st.subheader("🎯 Budget vs Aktual per Kategori")

try:
    df_cat = get_categories()
except gspread.exceptions.SpreadsheetNotFound:
    st.error(
        "Spreadsheet tidak ditemukan / belum di-share ke service account. "
        "Cek `SPREADSHEET_ID`/`SPREADSHEET_NAME` dan pastikan Google Sheet sudah di-share."
    )
    st.stop()
except gspread.exceptions.WorksheetNotFound:
    st.error("Worksheet `categories` tidak ditemukan. Buat sheet bernama `categories` di Google Sheet lo.")
    st.stop()

if df_cat.empty:
    st.info("Belum ada data kategori. Tambahkan budget limit dulu di halaman utama!")
else:
    # Hitung total pengeluaran per kategori bulan ini
    now = pd.Timestamp.today()
    df_keluar_valid = df_keluar[df_keluar["tanggal"].notna()].copy()
    df_bulan_ini = df_keluar_valid[
        (df_keluar_valid["tanggal"].dt.month == now.month)
        & (df_keluar_valid["tanggal"].dt.year == now.year)
    ]

    aktual = df_bulan_ini.groupby("kategori")["nominal"].sum().reset_index()
    aktual["nama_norm"] = aktual["kategori"].astype(str).str.strip().str.lower()
    aktual = aktual[["nama_norm", "nominal"]].rename(columns={"nominal": "aktual"})

    df_cat_norm = df_cat.copy()
    df_cat_norm["nama_norm"] = df_cat_norm["nama"].astype(str).str.strip().str.lower()

    # Gabungkan dengan budget limit (normalisasi key karena transaksi disimpan lowercase)
    budget_vs_aktual = df_cat_norm.merge(aktual, on="nama_norm", how="left").fillna({"aktual": 0})
    
    # Bikin bar chart perbandingan
    import plotly.graph_objects as go
    
    fig_budget = go.Figure()
    
    fig_budget.add_trace(go.Bar(
        name="Budget Limit",
        x=budget_vs_aktual["nama"],
        y=budget_vs_aktual["budget_limit"],
        marker_color="#3498db"
    ))
    
    fig_budget.add_trace(go.Bar(
        name="Aktual",
        x=budget_vs_aktual["nama"],
        y=budget_vs_aktual["aktual"],
        marker_color="#e74c3c"
    ))
    
    fig_budget.update_layout(
        barmode="group",
        xaxis_title="Kategori",
        yaxis_title="Nominal (Rp)"
    )
    
    st.plotly_chart(fig_budget, use_container_width=True)
    
    # ── Warning kalau over budget ───────────────
    st.subheader("⚠️ Status Budget Bulan Ini")
    
    for _, row in budget_vs_aktual.iterrows():
        if row["budget_limit"] == 0:
            continue
            
        persen = (row["aktual"] / row["budget_limit"]) * 100
        
        if persen >= 100:
            st.error(f"🔴 **{row['nama']}** — OVER BUDGET! ({persen:.0f}%)")
        elif persen >= 80:
            st.warning(f"🟡 **{row['nama']}** — Hampir habis ({persen:.0f}%)")
        else:
            st.success(f"🟢 **{row['nama']}** — Aman ({persen:.0f}%)")

# ── Insight Otomatis ────────────────────────────
st.subheader("🤖 Insight Bulan Ini")

insights = generate_insights(df)

for insight in insights:
    st.info(insight)
