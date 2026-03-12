#!/usr/bin/env python3
"""
Paper Trading Daily Scanner
============================
Runs DivergenceHunterStrategy on every symbol in the DB,
auto-opens/closes simulated positions, and saves state to:
    data/paper_trading/state.json

Designed to be called by GitHub Actions right after the daily OHLCV fetch.
State file is committed back to the repo, so the Streamlit dashboard always
shows fresh results without requiring a manual button press.

Usage:
    python scripts/run_paper_trading_scan.py
    python scripts/run_paper_trading_scan.py --initial-equity 70000
    python scripts/run_paper_trading_scan.py --max-positions 5 --dry-run
"""
import sys
import os
import argparse
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.infrastructure.database.connection import get_database
from src.infrastructure.database.repository import MarketDataRepository
from src.infrastructure.data_providers.yfinance_provider import YFinanceProvider
from src.application.services.data_service import DataService
from src.application.services.paper_trading_service import PaperTradingService


def main() -> None:
    parser = argparse.ArgumentParser(description="Paper trading daily scan")
    parser.add_argument("--initial-equity", type=float, default=70_000.0,
                        help="Starting equity in TWD (default: 70000)")
    parser.add_argument("--max-positions",  type=int,   default=5,
                        help="Max simultaneous open positions (default: 5)")
    parser.add_argument("--dry-run",        action="store_true",
                        help="Run scan but do NOT write state to disk")
    parser.add_argument("--force",          action="store_true",
                        help="Force re-scan even if today was already scanned")
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"  Paper Trading Daily Scan — {date.today().isoformat()}")
    print(f"  Initial equity : {args.initial_equity:,.0f} TWD")
    print(f"  Max positions  : {args.max_positions}")
    print(f"  Dry run        : {args.dry_run}")
    print(f"{'='*60}")

    # ── Bootstrap services ────────────────────────────────────────────────────
    db          = get_database()
    repository  = MarketDataRepository(db)
    provider    = YFinanceProvider()
    provider.connect()
    data_service = DataService(provider, repository)

    paper_service = PaperTradingService(initial_equity=args.initial_equity)

    if paper_service.already_scanned_today() and not args.force:
        print(f"✅ Today's scan already completed. Use --force to re-run.")
        _print_summary(paper_service.get_last_scan_summary())
        return

    # ── Progress display ──────────────────────────────────────────────────────
    _last_pct = [-1]

    def on_progress(current: int, total: int, symbol: str) -> None:
        pct = int(current / max(total, 1) * 100)
        if pct != _last_pct[0] and pct % 10 == 0:
            print(f"  [{pct:3d}%] {current}/{total}  {symbol}")
            _last_pct[0] = pct

    # ── Run scan ──────────────────────────────────────────────────────────────
    print("\nScanning symbols…")
    result = paper_service.run_daily_scan(
        data_service=data_service,
        max_positions=args.max_positions,
        progress_cb=on_progress,
    )

    if args.dry_run:
        print("\n[DRY RUN] State NOT written to disk.")
    else:
        print(f"\n✅ State saved → data/paper_trading/state.json")

    _print_summary(result)


def _print_summary(result: dict) -> None:
    print(f"\n{'─'*40}")
    print(f"  Scanned     : {result.get('scanned', '?')}")
    print(f"  New entries : {len(result.get('new_entries', []))}")
    for e in result.get("new_entries", []):
        print(f"    ▸ {e['symbol']}  @ {e['entry_price']:.2f}  "
              f"×{e['shares']} shares  pos={e['position_pct']*100:.0f}%  "
              f"score={e['signal_score']:.2f}")
    print(f"  Auto exits  : {len(result.get('auto_exits', []))}")
    for t in result.get("auto_exits", []):
        print(f"    ▸ {t['symbol']}  {t['exit_reason']}  "
              f"P&L {t['pnl_twd']:+,.0f} TWD ({t['pnl_pct']:+.2f}%)")
    print(f"  Skipped     : {len(result.get('skipped', []))}")
    errs = result.get("errors", [])
    if errs:
        print(f"  Errors      : {len(errs)}")
        for sym, err in errs[:5]:
            print(f"    ✗ {sym}: {err}")
    print(f"  Run at      : {result.get('run_at', '?')}")
    print(f"{'─'*40}\n")


if __name__ == "__main__":
    main()
