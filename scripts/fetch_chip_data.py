#!/usr/bin/env python3
"""
籌碼面資料抓取器 — Chip/Institutional Flow Data Fetcher
Fetches 三大法人 and 融資融券 data from TWSE for all Taiwan stocks.

Usage:
    python scripts/fetch_chip_data.py            # fetch last 5 trading days
    python scripts/fetch_chip_data.py --days 30  # fetch last 30 trading days
    python scripts/fetch_chip_data.py --full      # fetch last 2 years
"""
import sys
import os
import sqlite3
import argparse
import time
import json
from pathlib import Path
from datetime import date, timedelta

import requests
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

DB_PATH = ROOT / "data" / "database" / "market_data.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DinDinQuantBot/1.0)",
    "Referer": "https://www.twse.com.tw/",
}
REQUEST_DELAY = 1.5   # seconds between API calls — be polite to TWSE


# ── DB setup ──────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS institutional_flow (
            date         TEXT NOT NULL,
            symbol       TEXT NOT NULL,
            foreign_buy  REAL,
            foreign_sell REAL,
            foreign_net  REAL,
            invest_buy   REAL,
            invest_sell  REAL,
            invest_net   REAL,
            dealer_buy   REAL,
            dealer_sell  REAL,
            dealer_net   REAL,
            total_net    REAL,
            updated_at   TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (symbol, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS margin_trading (
            date           TEXT NOT NULL,
            symbol         TEXT NOT NULL,
            margin_buy     REAL,
            margin_sell    REAL,
            margin_balance REAL,
            short_sell     REAL,
            short_buy      REAL,
            short_balance  REAL,
            updated_at     TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (symbol, date)
        )
    """)
    conn.commit()
    return conn


# ── TWSE API helpers ───────────────────────────────────────────────────────────

def _to_num(val: str) -> float:
    """Convert TWSE comma-formatted string to float. Returns 0 on failure."""
    try:
        return float(str(val).replace(",", "").replace("+", "").strip())
    except (ValueError, AttributeError):
        return 0.0


def _twse_get(url: str) -> dict | None:
    """GET a TWSE JSON endpoint with retry logic."""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("stat") == "OK" and data.get("data"):
                    return data
                return None   # No data for this date (holiday / no-trading-day)
            time.sleep(2)
        except Exception as e:
            print(f"   ⚠️  Request error (attempt {attempt+1}): {e}")
            time.sleep(3)
    return None


# ── 三大法人 ───────────────────────────────────────────────────────────────────

def fetch_institutional_day(date_str: str) -> list[dict]:
    """
    Fetch T86 three-major-institutional data for all stocks on one date.
    date_str: YYYYMMDD

    Current TWSE T86 field layout (verified 2026-02):
    [0]  證券代號
    [1]  證券名稱
    [2]  外陸資買進股數 (不含外資自營商)  → foreign_buy
    [3]  外陸資賣出股數                  → foreign_sell
    [4]  外陸資買賣超股數                → foreign_net
    [5-7] 外資自營商 (excluded from foreign totals)
    [8]  投信買進股數                    → invest_buy
    [9]  投信賣出股數                    → invest_sell
    [10] 投信買賣超股數                  → invest_net
    [11] 自營商買賣超股數(合計)           → dealer_net
    [12] 自營商買進股數(自行買賣)         ─┐ dealer_buy
    [15] 自營商買進股數(避險)             ─┘
    [13] 自營商賣出股數(自行買賣)         ─┐ dealer_sell
    [16] 自營商賣出股數(避險)             ─┘
    [18] 三大法人買賣超股數               → total_net
    """
    url = (
        f"https://www.twse.com.tw/rwd/zh/fund/T86"
        f"?date={date_str}&selectType=ALLBUT0999&response=json"
    )
    data = _twse_get(url)
    if not data:
        return []

    date_iso = date_str[:4] + "-" + date_str[4:6] + "-" + date_str[6:]
    rows = []
    for item in data["data"]:
        try:
            symbol = str(item[0]).strip() + ".TW"
            rows.append({
                "date":         date_iso,
                "symbol":       symbol,
                "foreign_buy":  _to_num(item[2]),
                "foreign_sell": _to_num(item[3]),
                "foreign_net":  _to_num(item[4]),
                "invest_buy":   _to_num(item[8]),
                "invest_sell":  _to_num(item[9]),
                "invest_net":   _to_num(item[10]),
                "dealer_buy":   _to_num(item[12]) + _to_num(item[15]),
                "dealer_sell":  _to_num(item[13]) + _to_num(item[16]),
                "dealer_net":   _to_num(item[11]),
                "total_net":    _to_num(item[18]),
            })
        except (IndexError, Exception):
            continue
    return rows


def save_institutional(conn: sqlite3.Connection, rows: list[dict]) -> int:
    if not rows:
        return 0
    conn.executemany("""
        INSERT OR REPLACE INTO institutional_flow
        (date, symbol, foreign_buy, foreign_sell, foreign_net,
         invest_buy, invest_sell, invest_net,
         dealer_buy, dealer_sell, dealer_net, total_net)
        VALUES
        (:date, :symbol, :foreign_buy, :foreign_sell, :foreign_net,
         :invest_buy, :invest_sell, :invest_net,
         :dealer_buy, :dealer_sell, :dealer_net, :total_net)
    """, rows)
    conn.commit()
    return len(rows)


# ── 融資融券 ───────────────────────────────────────────────────────────────────

def fetch_margin_today() -> tuple[list[dict], str]:
    """
    Fetch today's 融資融券 data from TWSE OpenAPI (returns most recent trading day).

    Uses openapi.twse.com.tw which always returns the latest available date.
    Returns (rows, date_iso).

    OpenAPI field keys (verified 2026-02):
      股票代號, 融資買進, 融資賣出, 融資前日餘額, 融資今日餘額,
      融券買進, 融券賣出, 融券前日餘額, 融券今日餘額
    """
    url = "https://openapi.twse.com.tw/v1/exchangeReport/MI_MARGN"
    today_iso = date.today().isoformat()
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return [], today_iso
        data = resp.json()
        if not isinstance(data, list) or not data:
            return [], today_iso
    except Exception as e:
        print(f"   ⚠️  MI_MARGN fetch error: {e}")
        return [], today_iso

    rows = []
    for item in data:
        try:
            symbol = str(item.get("股票代號", "")).strip() + ".TW"
            rows.append({
                "date":           today_iso,
                "symbol":         symbol,
                "margin_buy":     _to_num(item.get("融資買進", 0)),
                "margin_sell":    _to_num(item.get("融資賣出", 0)),
                "margin_balance": _to_num(item.get("融資今日餘額", 0)),
                "short_sell":     _to_num(item.get("融券賣出", 0)),
                "short_buy":      _to_num(item.get("融券買進", 0)),
                "short_balance":  _to_num(item.get("融券今日餘額", 0)),
            })
        except Exception:
            continue
    return rows, today_iso


def save_margin(conn: sqlite3.Connection, rows: list[dict]) -> int:
    if not rows:
        return 0
    conn.executemany("""
        INSERT OR REPLACE INTO margin_trading
        (date, symbol, margin_buy, margin_sell, margin_balance,
         short_sell, short_buy, short_balance)
        VALUES
        (:date, :symbol, :margin_buy, :margin_sell, :margin_balance,
         :short_sell, :short_buy, :short_balance)
    """, rows)
    conn.commit()
    return len(rows)


# ── Date helpers ───────────────────────────────────────────────────────────────

def _trading_dates(days_back: int) -> list[str]:
    """
    Return last N calendar days as YYYYMMDD strings.
    TWSE API silently returns no data for holidays — safe to include all days.
    """
    today = date.today()
    return [
        (today - timedelta(days=i)).strftime("%Y%m%d")
        for i in range(days_back, 0, -1)   # oldest → newest
    ]


def _already_fetched(conn: sqlite3.Connection, date_iso: str) -> bool:
    """Return True if we already have institutional data for this date."""
    row = conn.execute(
        "SELECT COUNT(*) FROM institutional_flow WHERE date=?", (date_iso,)
    ).fetchone()
    return row[0] > 0


# ── Main runner ────────────────────────────────────────────────────────────────

def run(days_back: int = 5):
    conn = get_db()
    dates = _trading_dates(days_back)

    total_inst = 0
    skipped = 0

    print(f"\n{'='*60}")
    print(f"📊 Fetching chip data | last {days_back} days")
    print(f"{'='*60}\n")

    # ── 三大法人: date-by-date historical fetch ───────────────────────────────
    for date_str in dates:
        date_iso = date_str[:4] + "-" + date_str[4:6] + "-" + date_str[6:]

        if _already_fetched(conn, date_iso):
            print(f"[{date_iso}] ⏭️  already in DB — skipped")
            skipped += 1
            continue

        print(f"[{date_iso}] 三大法人 ...", end=" ", flush=True)
        inst_rows = fetch_institutional_day(date_str)
        n_inst = save_institutional(conn, inst_rows)
        print(f"{n_inst} stocks")
        time.sleep(REQUEST_DELAY)
        total_inst += n_inst

    # ── 融資融券: OpenAPI returns latest trading day only ─────────────────────
    print(f"\n[today] 融資融券 (OpenAPI latest) ...", end=" ", flush=True)
    margin_rows, margin_date = fetch_margin_today()
    total_margin = save_margin(conn, margin_rows)
    print(f"{total_margin} stocks  (date: {margin_date})")

    conn.close()
    print(f"\n{'='*60}")
    print(f"✅ 三大法人: {total_inst} rows | 融資融券: {total_margin} rows | ⏭️ Skipped: {skipped} days")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days",  type=int, default=5,   help="Days back to fetch (default: 5)")
    parser.add_argument("--full",  action="store_true",    help="Fetch full 2-year history")
    args = parser.parse_args()

    days = 730 if args.full else args.days
    run(days_back=days)
