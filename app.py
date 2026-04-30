import streamlit as st
from ui.categories_tab import render_categories_tab
from ui.goals_tab import render_goals_tab
from ui.transactions_tab import render_transactions_tab

st.title("💰 Personal Finance Tracker")

tab_transaksi, tab_kategori, tab_goals = st.tabs(["Transaksi", "Kategori", "Goals"])

with tab_transaksi:
    render_transactions_tab()

with tab_kategori:
    render_categories_tab()

with tab_goals:
    render_goals_tab()
