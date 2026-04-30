from __future__ import annotations

import re
from typing import Final


_GOAL_ID_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"\[goal_id:[^\]]+\]\s*", re.IGNORECASE)


def strip_goal_id_token(text: str) -> str:
    return _GOAL_ID_TOKEN_RE.sub("", str(text or "")).strip()


def format_rupiah(value: float, *, sign: str | None = None) -> str:
    amount = float(value or 0)
    prefix = "Rp "
    if sign:
        prefix += f"{sign}"
    return f"{prefix}{amount:,.0f}"


def format_nominal_signed(tipe: str, nominal: float) -> str:
    tipe_norm = str(tipe or "").lower()
    sign = "-" if tipe_norm == "pengeluaran" else "+"
    return format_rupiah(float(nominal or 0), sign=sign)


def style_nominal_color(tipe: str) -> str:
    tipe_norm = str(tipe or "").lower()
    if tipe_norm == "pemasukan":
        return "#2ecc71"
    if tipe_norm == "refunds":
        return "#f39c12"
    return "#e74c3c"

