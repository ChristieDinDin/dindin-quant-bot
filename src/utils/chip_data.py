"""
籌碼面資料查詢工具 — Chip/Institutional Flow Data Helpers

Provides query functions for institutional_flow and margin_trading tables.
Used by the dashboard chip_analysis component.
"""
import sqlite3
import pandas as pd
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "database" / "market_data.db"


def _get_conn() -> sqlite3.Connection:
    """Get a read-only-ish connection to the market data DB."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ── Institutional Flow (三大法人) ──────────────────────────────────────────────

def get_institutional_flow(symbol: str, days: int = 30) -> pd.DataFrame:
    """
    Return last `days` rows of 三大法人 data for a symbol.

    Columns: date, foreign_buy, foreign_sell, foreign_net,
             invest_buy, invest_sell, invest_net,
             dealer_buy, dealer_sell, dealer_net, total_net
    """
    conn = _get_conn()
    try:
        df = pd.read_sql_query(
            """
            SELECT date,
                   foreign_buy, foreign_sell, foreign_net,
                   invest_buy,  invest_sell,  invest_net,
                   dealer_buy,  dealer_sell,  dealer_net,
                   total_net
            FROM institutional_flow
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            conn,
            params=(symbol, days),
        )
    finally:
        conn.close()

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


# ── Margin Trading (融資融券) ──────────────────────────────────────────────────

def get_margin_trading(symbol: str, days: int = 30) -> pd.DataFrame:
    """
    Return last `days` rows of 融資融券 data for a symbol.

    Columns: date, margin_buy, margin_sell, margin_balance,
             short_sell, short_buy, short_balance,
             margin_change, short_change
    """
    conn = _get_conn()
    try:
        df = pd.read_sql_query(
            """
            SELECT date,
                   margin_buy, margin_sell, margin_balance,
                   short_sell, short_buy,   short_balance
            FROM margin_trading
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            conn,
            params=(symbol, days),
        )
    finally:
        conn.close()

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Compute day-over-day changes
    df["margin_change"] = df["margin_balance"].diff()
    df["short_change"]  = df["short_balance"].diff()

    return df


# ── Signal helpers ─────────────────────────────────────────────────────────────

def consecutive_days(series: pd.Series, positive: bool = True) -> int:
    """
    Count how many consecutive days the series has been positive (or negative).

    positive=True  → count streak of values > 0
    positive=False → count streak of values < 0
    """
    if series.empty:
        return 0
    streak = 0
    for val in reversed(series.tolist()):
        if pd.isna(val):
            break
        if positive and val > 0:
            streak += 1
        elif not positive and val < 0:
            streak += 1
        else:
            break
    return streak


def chip_summary(symbol: str) -> dict:
    """
    Return a compact summary dict for the signal cards:
    {
      foreign_net_today, foreign_streak,
      invest_net_today,  invest_streak,
      dealer_net_today,  dealer_streak,
      total_net_today,
      margin_balance, margin_change,
      short_balance,  short_change,
      has_data: bool
    }
    """
    inst = get_institutional_flow(symbol, days=20)
    margin = get_margin_trading(symbol, days=5)

    if inst.empty:
        return {"has_data": False}

    last_inst = inst.iloc[-1]

    foreign_streak = consecutive_days(inst["foreign_net"], positive=(last_inst["foreign_net"] >= 0))
    invest_streak  = consecutive_days(inst["invest_net"],  positive=(last_inst["invest_net"] >= 0))
    dealer_streak  = consecutive_days(inst["dealer_net"],  positive=(last_inst["dealer_net"] >= 0))

    result = {
        "has_data":          True,
        "latest_date":       last_inst["date"].strftime("%Y-%m-%d"),
        "foreign_net_today": last_inst["foreign_net"],
        "foreign_buy_today":  last_inst["foreign_buy"],
        "foreign_sell_today": last_inst["foreign_sell"],
        "foreign_streak":    foreign_streak,
        "foreign_positive":  last_inst["foreign_net"] >= 0,
        "invest_net_today":  last_inst["invest_net"],
        "invest_buy_today":   last_inst["invest_buy"],
        "invest_sell_today":  last_inst["invest_sell"],
        "invest_streak":     invest_streak,
        "invest_positive":   last_inst["invest_net"] >= 0,
        "dealer_net_today":  last_inst["dealer_net"],
        "dealer_buy_today":   last_inst["dealer_buy"],
        "dealer_sell_today":  last_inst["dealer_sell"],
        "dealer_streak":     dealer_streak,
        "dealer_positive":   last_inst["dealer_net"] >= 0,
        "total_net_today":   last_inst["total_net"],
    }

    if not margin.empty:
        last_m = margin.iloc[-1]
        result.update({
            "margin_balance": last_m["margin_balance"],
            "margin_change":  last_m["margin_change"],
            "short_balance":  last_m["short_balance"],
            "short_change":   last_m["short_change"],
        })

    return result


def has_chip_data(symbol: str) -> bool:
    """Quick check: does this symbol have any chip data in the DB?"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM institutional_flow WHERE symbol=? LIMIT 1", (symbol,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()
