import streamlit as st
import plotly.express as px
import pandas as pd
from insight import generate_insights
from services.finance_math import compute_summary
from services.gsheet_loaders import load_categories, load_transactions

st.title("📊 Dashboard")
st.divider()

df = load_transactions(stop=True)

if df.empty:
    st.warning("Belum ada data transaksi. Tambahkan dulu di halaman utama!")
    st.stop()

# ── Summary Cards ──────────────────────────────
summary = compute_summary(df)

col1, col2, col3 = st.columns(3)
col1.metric("💵 Total Pemasukan", f"Rp {summary.total_masuk:,.0f}")
col2.metric("💸 Total Pengeluaran", f"Rp {summary.total_keluar_net:,.0f}")
col3.metric("🏦 Saldo", f"Rp {summary.saldo:,.0f}", 
            delta=f"Rp {summary.saldo:,.0f}",
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
    st.plotly_chart(fig_pie, width="stretch")

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
st.plotly_chart(fig_bar, width="stretch")

# ── Chart 3: Budget vs Aktual ───────────────────
st.subheader("🎯 Budget vs Aktual per Kategori")

df_cat = load_categories(stop=True)

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

    # Refunds (dari hapus goals) harus mengurangi aktual kategori "goals"
    df_refunds_valid = df[(df["tipe"] == "refunds") & df["tanggal"].notna()].copy()
    df_refunds_bulan_ini = df_refunds_valid[
        (df_refunds_valid["tanggal"].dt.month == now.month)
        & (df_refunds_valid["tanggal"].dt.year == now.year)
    ]

    net_by_category = (
        df_bulan_ini.groupby("kategori")["nominal"].sum().astype(float).to_dict()
    )
    refunds_total = float(df_refunds_bulan_ini["nominal"].sum() or 0)
    if refunds_total:
        net_by_category["goals"] = float(net_by_category.get("goals", 0)) - refunds_total
        if net_by_category["goals"] < 0:
            net_by_category["goals"] = 0.0

    aktual = pd.DataFrame(
        [{"nama_norm": str(k).strip().lower(), "aktual": float(v)} for k, v in net_by_category.items()]
    )

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
    
    st.plotly_chart(fig_budget, width="stretch")
    
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
