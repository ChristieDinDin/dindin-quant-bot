#!/usr/bin/env python3
"""
Daily stock data fetcher for GitHub Actions.
Uses only yfinance — no shioaji, no heavy dependencies.

Fetches all stocks from data/us_stocks.yaml and data/taiwan_stocks.yaml
and saves them to the SQLite database.

Usage:
    python scripts/fetch_all_stocks.py            # incremental (last 7 days)
    python scripts/fetch_all_stocks.py --full     # full history (2 years)
    python scripts/fetch_all_stocks.py --years 5  # full history (N years)
"""
import sys
import os
import sqlite3
import argparse
from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import yfinance as yf
import yaml

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

DB_PATH = ROOT / "data" / "database" / "market_data.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ── Database helpers ──────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    # Match existing schema: date, symbol, open, high, low, close, volume, updated_at
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_kline (
            date       TEXT NOT NULL,
            symbol     TEXT NOT NULL,
            open       REAL, high REAL, low REAL, close REAL, volume REAL,
            updated_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (symbol, date)
        )
    """)
    conn.commit()
    return conn


def last_date_for(conn, symbol: str):
    row = conn.execute(
        "SELECT MAX(date) FROM daily_kline WHERE symbol=?", (symbol,)
    ).fetchone()
    return row[0] if row and row[0] else None


def save_df(conn, df: pd.DataFrame, symbol: str) -> int:
    if df.empty:
        return 0
    df = df.copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    now = pd.Timestamp.now().isoformat()
    rows = [
        (str(idx.date()), symbol, row["Open"], row["High"],
         row["Low"], row["Close"], row["Volume"], now)
        for idx, row in df.iterrows()
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO daily_kline (date,symbol,open,high,low,close,volume,updated_at) VALUES (?,?,?,?,?,?,?,?)",
        rows
    )
    conn.commit()
    return len(rows)


# ── Symbol loading ─────────────────────────────────────────────────────────────

def load_symbols() -> list:
    seen, symbols = set(), []
    for fname in ["taiwan_stocks.yaml", "us_stocks.yaml"]:
        f = ROOT / "data" / fname
        if not f.exists():
            continue
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for cat in data.values():
            if isinstance(cat, dict):
                for sym in cat:
                    if sym not in seen:
                        seen.add(sym)
                        symbols.append(sym)
    return symbols


# ── Fetch ─────────────────────────────────────────────────────────────────────

def fetch_symbol(symbol: str, start: date, end: date) -> pd.DataFrame:
    try:
        df = yf.download(symbol, start=str(start), end=str(end),
                         progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    except Exception as e:
        print(f"   ⚠️  {symbol}: {e}")
        return pd.DataFrame()


def run(full: bool = False, years: int = 2):
    conn = get_db()
    symbols = load_symbols()
    today = date.today()

    print(f"\n{'='*60}")
    print(f"📦 Fetching {len(symbols)} stocks | mode={'full' if full else 'incremental'}")
    print(f"{'='*60}\n")

    success, skipped, failed = 0, 0, []

    for i, sym in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {sym} ...", end=" ")

        if full:
            start = today - timedelta(days=365 * years)
        else:
            last = last_date_for(conn, sym)
            if last:
                start = date.fromisoformat(last) + timedelta(days=1)
                if start >= today:
                    print("✅ up-to-date")
                    skipped += 1
                    continue
            else:
                start = today - timedelta(days=365 * years)

        df = fetch_symbol(sym, start, today)
        if df.empty:
            print("⚠️  no data")
            failed.append(sym)
            continue

        n = save_df(conn, df, sym)
        print(f"✅ {n} rows")
        success += 1

    conn.close()
    print(f"\n{'='*60}")
    print(f"✅ Success: {success} | ⏭️ Skipped: {skipped} | ❌ Failed: {len(failed)}")
    if failed:
        print(f"Failed: {', '.join(failed)}")
    print(f"DB: {DB_PATH} ({DB_PATH.stat().st_size // 1024} KB)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Full history fetch")
    parser.add_argument("--years", type=int, default=2, help="Years of history (default: 2)")
    args = parser.parse_args()
    run(full=args.full, years=args.years)
