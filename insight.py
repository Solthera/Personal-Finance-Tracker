from datetime import datetime

def generate_insights(df):
    insights = []
    
    if df.empty:
        return ["Belum ada data transaksi untuk dianalisis."]
    
    bulan_ini = datetime.now().month
    tahun_ini = datetime.now().year
    
    df_bulan = df[
        (df["tanggal"].dt.month == bulan_ini) &
        (df["tanggal"].dt.year == tahun_ini)
    ]
    
    df_keluar = df_bulan[df_bulan["tipe"] == "pengeluaran"]
    df_masuk = df_bulan[df_bulan["tipe"] == "pemasukan"]
    
    # ── Insight 1: Kategori terboros ───────────
    if not df_keluar.empty:
        terboros = df_keluar.groupby("kategori")["nominal"].sum().idxmax()
        nominal_terboros = df_keluar.groupby("kategori")["nominal"].sum().max()
        insights.append(
            f"💸 Pengeluaran terbesar lo bulan ini ada di kategori "
            f"**{terboros}** sebesar **Rp {nominal_terboros:,.0f}**"
        )
    
    # ── Insight 2: Rasio pengeluaran vs pemasukan ──
    total_masuk = df_masuk["nominal"].sum()
    total_keluar = df_keluar["nominal"].sum()
    
    if total_masuk > 0:
        rasio = (total_keluar / total_masuk) * 100
        if rasio >= 90:
            insights.append(
                f"⚠️ Lo udah ngabisin **{rasio:.0f}%** dari pemasukan bulan ini — "
                f"mulai hati-hati!"
            )
        elif rasio >= 70:
            insights.append(
                f"📊 Lo udah ngabisin **{rasio:.0f}%** dari pemasukan bulan ini — "
                f"masih oke tapi perhatiin pengeluaran lo."
            )
        else:
            insights.append(
                f"✅ Keuangan lo sehat! Baru ngabisin **{rasio:.0f}%** "
                f"dari pemasukan bulan ini."
            )
    
    # ── Insight 3: Hari paling boros ───────────
    if not df_keluar.empty:
        df_keluar = df_keluar.copy()
        df_keluar["hari"] = df_keluar["tanggal"].dt.day_name()
        hari_boros = df_keluar.groupby("hari")["nominal"].sum().idxmax()
        insights.append(
            f"📅 Hari paling boros lo adalah **{hari_boros}** — "
            f"coba lebih aware di hari itu!"
        )
    
    # ── Insight 4: Frekuensi transaksi ─────────
    jumlah_transaksi = len(df_bulan)
    insights.append(
        f"🔢 Lo udah melakukan **{jumlah_transaksi} transaksi** bulan ini."
    )
    
    return insights