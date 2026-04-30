from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Summary:
    total_masuk: float
    total_keluar_gross: float
    total_refunds: float
    total_keluar_net: float
    saldo: float


def compute_summary(df_transactions) -> Summary:
    if df_transactions is None or getattr(df_transactions, "empty", True):
        return Summary(
            total_masuk=0.0,
            total_keluar_gross=0.0,
            total_refunds=0.0,
            total_keluar_net=0.0,
            saldo=0.0,
        )

    df = df_transactions
    total_masuk = float(df[df["tipe"] == "pemasukan"]["nominal"].sum() or 0)
    total_refunds = float(df[df["tipe"] == "refunds"]["nominal"].sum() or 0)
    total_keluar_gross = float(df[df["tipe"] == "pengeluaran"]["nominal"].sum() or 0)
    total_keluar_net = float(total_keluar_gross - total_refunds)
    saldo = float(total_masuk - total_keluar_gross + total_refunds)

    return Summary(
        total_masuk=total_masuk,
        total_keluar_gross=total_keluar_gross,
        total_refunds=total_refunds,
        total_keluar_net=total_keluar_net,
        saldo=saldo,
    )


def compute_saldo(df_transactions) -> float:
    return compute_summary(df_transactions).saldo

