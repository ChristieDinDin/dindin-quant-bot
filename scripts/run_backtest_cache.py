#!/usr/bin/env python3
"""
Nightly Backtest Cache Builder
================================
Run after daily OHLCV import to pre-compute and cache backtest results for
all symbols in the DB, using default strategy parameters.

When the user opens Backtest Lab, results load instantly from cache.
Cache TTL = 36 hours (survives weekends; refreshed nightly on weekdays).

Usage:
    python scripts/run_backtest_cache.py                     # all strategies
    python scripts/run_backtest_cache.py --strategy mfi_hunter
    python scripts/run_backtest_cache.py --limit 50          # test run
    python scripts/run_backtest_cache.py --workers 4         # parallel (faster)
"""
import sys
import os
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.infrastructure.database.connection import DatabaseConnection
from src.infrastructure.database.repository import MarketDataRepository
from src.infrastructure.database.backtest_cache import (
    BacktestCacheRepository,
    make_params_hash,
)
from src.infrastructure.data_providers.yfinance_provider import YFinanceProvider
from src.application.services.data_service import DataService
from src.application.services.backtest_service import BacktestService
from src.application.use_cases.run_backtest import RunBacktestUseCase
from src.core.strategies.registry import get_global_registry

DB_PATH = str(ROOT / "data" / "database" / "market_data.db")

# ── Default parameters per strategy ──────────────────────────────────────────
DEFAULT_PARAMS = {
    "mfi_hunter": {
        "strategy_params": {"mfi_period": 14, "buy_threshold": 20, "sell_threshold": 80},
        "cash": 1_000_000,
        "commission": 0.001425,
    },
    "rsi_mfi_consensus": {
        "strategy_params": {
            "mfi_period": 14, "rsi_period": 14,
            "mfi_oversold": 20, "mfi_overbought": 80,
            "rsi_oversold": 30, "rsi_overbought": 70,
        },
        "cash": 1_000_000,
        "commission": 0.001425,
    },
    "divergence_hunter": {
        "strategy_params": {
            "mfi_period": 14, "rsi_period": 14,
            "rsi_oversold": 35, "rsi_overbought": 70,
        },
        "cash": 1_000_000,
        "commission": 0.001425,
    },
}

CACHE_TTL_HOURS = 36  # nightly build: expires after 36h (covers weekends)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_all_db_symbols(repo: MarketDataRepository) -> list[str]:
    return sorted(repo.get_all_symbols())


def get_data_last_date(repo: MarketDataRepository, symbol: str) -> str:
    dr = repo.get_date_range(symbol)
    return dr[1].isoformat() if dr else date.today().isoformat()


def run_one(
    symbol: str,
    strategy_name: str,
    cfg: dict,
    use_case: RunBacktestUseCase,
    repo: MarketDataRepository,
    cache: BacktestCacheRepository,
) -> tuple[str, bool, str]:
    """Run backtest for one symbol and store in cache. Returns (symbol, ok, msg)."""
    params_hash = make_params_hash(cfg["strategy_params"], cfg["cash"], cfg["commission"])

    # Skip if cache is still fresh
    existing = cache.get(symbol, strategy_name, params_hash)
    if existing:
        return symbol, True, "cache_hit"

    try:
        result = use_case.execute(
            symbol=symbol,
            strategy_name=strategy_name,
            strategy_params=cfg["strategy_params"],
            cash=cfg["cash"],
            commission=cfg["commission"],
        )
        if not result.get("success"):
            return symbol, False, result.get("error", "unknown")

        data_last_date = get_data_last_date(repo, symbol)
        cache.set(symbol, strategy_name, params_hash, result, data_last_date, CACHE_TTL_HOURS)
        return symbol, True, "computed"

    except Exception as e:
        return symbol, False, str(e)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Nightly backtest cache builder")
    parser.add_argument("--strategy", default="all",
                        help="Strategy to cache (default: all). Options: mfi_hunter, rsi_mfi_consensus, divergence_hunter, all")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of symbols (for testing)")
    parser.add_argument("--workers", type=int, default=2,
                        help="Parallel workers (default: 2; more = faster but heavier on CPU)")
    parser.add_argument("--force", action="store_true",
                        help="Rebuild cache even if already fresh")
    args = parser.parse_args()

    strategies = list(DEFAULT_PARAMS.keys()) if args.strategy == "all" else [args.strategy]

    # Setup services
    db = DatabaseConnection(DB_PATH)
    repo = MarketDataRepository(db)
    cache = BacktestCacheRepository(DB_PATH)

    provider = YFinanceProvider()
    provider.connect()
    ds = DataService(provider, repo)
    bt = BacktestService(ds)
    use_case = RunBacktestUseCase(bt, ds)

    symbols = get_all_db_symbols(repo)
    if args.limit:
        symbols = symbols[: args.limit]

    # Force-expire cache if --force
    if args.force:
        print("⚠️  --force: invalidating existing cache entries...")
        # We skip the cache_hit check by monkey-patching (simple approach)
        _orig_get = cache.get
        cache.get = lambda *a, **kw: None

    t_start = time.monotonic()

    for strategy_name in strategies:
        if strategy_name not in DEFAULT_PARAMS:
            print(f"❌ Unknown strategy: {strategy_name}")
            continue

        cfg = DEFAULT_PARAMS[strategy_name]
        params_hash = make_params_hash(cfg["strategy_params"], cfg["cash"], cfg["commission"])

        print(f"\n{'='*60}")
        print(f"📐 Strategy: {strategy_name}")
        print(f"   Symbols: {len(symbols)} | Workers: {args.workers}")
        print(f"   Params hash: {params_hash}")
        print(f"{'='*60}")

        ok_count = 0
        skip_count = 0
        fail_count = 0
        failures = []

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(run_one, sym, strategy_name, cfg, use_case, repo, cache): sym
                for sym in symbols
            }
            for i, future in enumerate(as_completed(futures), 1):
                sym, ok, msg = future.result()
                if ok:
                    if msg == "cache_hit":
                        skip_count += 1
                    else:
                        ok_count += 1
                else:
                    fail_count += 1
                    failures.append(f"{sym}: {msg}")

                # Progress every 50
                if i % 50 == 0 or i == len(symbols):
                    elapsed = time.monotonic() - t_start
                    pct = i / len(symbols) * 100
                    print(f"  [{i:4d}/{len(symbols)}] {pct:.0f}% | "
                          f"computed={ok_count} skip={skip_count} fail={fail_count} "
                          f"| {elapsed:.0f}s elapsed")

        print(f"\n✅ Done: computed={ok_count} | skipped(cache fresh)={skip_count} | failed={fail_count}")
        if failures:
            print(f"   Failed samples: {failures[:5]}")

    # Purge old expired rows
    purged = cache.purge_expired()
    stats = cache.stats()

    total_elapsed = time.monotonic() - t_start
    print(f"\n{'='*60}")
    print(f"🗄️  Cache stats: {stats['valid_rows']} valid rows | {purged} expired purged")
    print(f"   By strategy: {stats['by_strategy']}")
    print(f"⏱️  Total time: {total_elapsed:.1f}s")
    print(f"{'='*60}\n")

    # Write summary for GitHub Actions
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(f"\n### 🗃️ Backtest Cache\n")
            f.write(f"- Valid entries: **{stats['valid_rows']}**\n")
            f.write(f"- By strategy: {stats['by_strategy']}\n")
            f.write(f"- Time: {total_elapsed:.0f}s\n")


if __name__ == "__main__":
    main()
