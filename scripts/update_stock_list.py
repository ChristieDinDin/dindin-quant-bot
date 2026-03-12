#!/usr/bin/env python3
"""
Taiwan Stock List Updater — Volume-Based Selection
====================================================
Fetches ALL listed/OTC Taiwan stocks from TWSE & TPEX OpenAPI,
filters by minimum average daily trading value, and writes the
results into the `high_volume` section of data/taiwan_stocks.yaml.

Why value-based (not share-count-based)?
  Low-price stocks have huge share volumes but tiny liquidity.
  Trading *value* (TWD) is the right proxy for "active enough to trade".

Usage:
    python scripts/update_stock_list.py                # default: ≥ 50M TWD/day
    python scripts/update_stock_list.py --min-value 100  # stricter: ≥ 100M TWD/day
    python scripts/update_stock_list.py --min-value 20   # looser: ≥ 20M TWD/day
    python scripts/update_stock_list.py --dry-run        # preview only

API sources (no auth needed):
    TWSE: https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL
    TPEX: https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes
"""
import sys
import os
import argparse
import json
from pathlib import Path
from datetime import date

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "taiwan_stocks.yaml"

TWSE_DAY_ALL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TPEX_DAY_ALL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"

HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}


# ── TWSE ──────────────────────────────────────────────────────────────────────

def _is_etf(code: str) -> bool:
    """ETFs on TWSE start with '0' (0050 etc); on TPEX have 6 digits."""
    return code.startswith("0") or len(code) != 4


def fetch_twse(min_value_million: float, include_etf: bool = False) -> dict[str, str]:
    """Return {symbol: name} for TWSE stocks with daily value >= min_value_million TWD."""
    print("📡 Fetching TWSE data...")
    try:
        r = requests.get(TWSE_DAY_ALL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        rows = r.json()
    except Exception as e:
        print(f"   ⚠️  TWSE API error: {e}")
        return {}

    result = {}
    threshold = min_value_million * 1_000_000

    for row in rows:
        code = str(row.get("Code", "")).strip()
        name = str(row.get("Name", "")).strip()
        # TWSE returns value in TWD
        value_str = str(row.get("TradeValue", "0")).replace(",", "")

        if not code or not name:
            continue
        if not code.isdigit():
            continue
        if not include_etf and _is_etf(code):
            continue

        try:
            value = float(value_str)
        except ValueError:
            continue

        if value >= threshold:
            symbol = f"{code}.TW"
            result[symbol] = name

    print(f"   ✅ TWSE: {len(result)} stocks above {min_value_million}M TWD/day")
    return result


# ── TPEX ──────────────────────────────────────────────────────────────────────

def fetch_tpex(min_value_million: float, include_etf: bool = False) -> dict[str, str]:
    """Return {symbol: name} for TPEX stocks with daily value >= min_value_million TWD."""
    print("📡 Fetching TPEX data...")
    try:
        r = requests.get(TPEX_DAY_ALL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        rows = r.json()
    except Exception as e:
        print(f"   ⚠️  TPEX API error: {e}")
        return {}

    result = {}
    threshold = min_value_million * 1_000_000

    for row in rows:
        code = str(row.get("SecuritiesCompanyCode", "")).strip()
        name = str(row.get("CompanyName", "")).strip()
        # TransactionAmount is in TWD (confirmed from API sample)
        value_raw = str(row.get("TransactionAmount", "0")).replace(",", "")

        if not code or not name:
            continue
        if not code.isdigit():
            continue
        if not include_etf and _is_etf(code):
            continue

        try:
            value = float(value_raw)
        except ValueError:
            continue

        if value >= threshold:
            symbol = f"{code}.TWO"
            result[symbol] = name

    print(f"   ✅ TPEX: {len(result)} stocks above {min_value_million}M TWD/day")
    return result


# ── YAML update ───────────────────────────────────────────────────────────────

def get_no_data_streak(symbol: str, db_path: str) -> int:
    """
    Returns how many calendar days since this symbol last had data in the DB.
    Returns 0 if data exists recently, 9999 if symbol never existed.
    """
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT MAX(date) FROM daily_kline WHERE symbol = ?", (symbol,)
        ).fetchone()
        conn.close()
        if not row or not row[0]:
            return 9999
        last = date.fromisoformat(row[0])
        # Ignore weekends: count only trading day gaps roughly
        return (date.today() - last).days
    except Exception:
        return 9999


def update_yaml(
    new_stocks: dict[str, str],
    min_value_million: float,
    dry_run: bool,
    stale_days: int = 45,
):
    """
    Append-only update: only ADD new stocks to high_volume section.
    Never removes existing stocks UNLESS they've had no DB data for stale_days days
    (i.e. truly delisted — yfinance has been returning empty for weeks).

    This protects:
    - Stocks you may be holding
    - Stocks that temporarily drop below the volume threshold
    """
    yaml_data = yaml.safe_load(DATA_FILE.read_text(encoding="utf-8")) or {}
    existing_high_vol = yaml_data.get("high_volume", {})

    # Determine DB path
    db_path = str(ROOT / "data" / "database" / "market_data.db")

    # ── Find truly stale symbols (delisted) ──────────────────────────────
    stale = []
    if existing_high_vol and ROOT.joinpath("data/database/market_data.db").exists():
        for sym in existing_high_vol:
            streak = get_no_data_streak(sym, db_path)
            if streak >= stale_days:
                stale.append(sym)

    # ── Build merged list: keep all existing + add new ───────────────────
    merged = dict(existing_high_vol)  # start with everything we already have

    # Remove only truly stale (delisted) symbols
    removed = []
    for sym in stale:
        if sym not in new_stocks:  # don't remove if it's back in today's active list
            del merged[sym]
            removed.append(sym)

    # Add new symbols (update names too)
    added = []
    for sym, name in new_stocks.items():
        if sym not in merged:
            merged[sym] = name
            added.append(sym)
        else:
            merged[sym] = name  # refresh name in case it changed

    print(f"\n📊 Summary")
    print(f"   Existing: {len(existing_high_vol)} stocks")
    print(f"   Added:    {len(added)} new stocks")
    print(f"   Removed:  {len(removed)} truly stale (≥{stale_days} days no data)")
    print(f"   Total:    {len(merged)} stocks")
    print(f"   Filter:   ≥ {min_value_million}M TWD/day  |  Date: {date.today()}")

    if removed:
        print(f"   Removed stocks: {', '.join(removed[:10])}" + (" ..." if len(removed) > 10 else ""))
    if added:
        print(f"   Sample new: {', '.join(added[:10])}" + (" ..." if len(added) > 10 else ""))

    if dry_run:
        print("\n🔍 Dry-run mode — no file written.")
        return

    yaml_data["high_volume"] = merged

    header = f"""# Taiwan Stock Master List
# This file contains stock codes and their Chinese/English names
# Source: TWSE + TPEX OpenAPI
# Last Updated: {date.today()} | {len(merged)} stocks | ≥{min_value_million}M TWD/day
# Policy: append-only (stocks removed only after ≥{stale_days} days with no data)

"""
    body = yaml.dump(
        yaml_data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        indent=2,
    )
    DATA_FILE.write_text(header + body, encoding="utf-8")
    print(f"\n✅ Saved to {DATA_FILE}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Update taiwan_stocks.yaml with volume-filtered stocks"
    )
    parser.add_argument(
        "--min-value", type=float, default=50.0,
        help="Minimum average daily trading value in million TWD (default: 50)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview results without writing to file"
    )
    parser.add_argument(
        "--include-etf", action="store_true",
        help="Include ETFs (default: stocks only)"
    )
    parser.add_argument(
        "--stale-days", type=int, default=45,
        help="Remove existing stocks with no DB data for this many days (default: 45 = ~2 months)"
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"🇹🇼 Taiwan Stock List Updater")
    print(f"   Min daily trading value: ≥ {args.min_value}M TWD")
    print(f"   ETFs: {'included' if args.include_etf else 'excluded'}")
    print(f"   Stale threshold: {args.stale_days} days")
    print(f"{'='*60}\n")

    twse = fetch_twse(args.min_value, include_etf=args.include_etf)
    tpex = fetch_tpex(args.min_value, include_etf=args.include_etf)
    all_stocks = {**twse, **tpex}

    if not all_stocks:
        print("❌ No stocks fetched. Check your internet connection.")
        sys.exit(1)

    print(f"\n📦 Total qualifying stocks: {len(all_stocks)}")
    print(f"   TWSE: {len(twse)}  |  TPEX: {len(tpex)}")

    update_yaml(all_stocks, args.min_value, dry_run=args.dry_run, stale_days=args.stale_days)

    if not args.dry_run:
        print(f"\n💡 Next: run the following to import new stocks into your DB:")
        print(f"   python scripts/fetch_all_stocks.py --full --years 2")


if __name__ == "__main__":
    main()
