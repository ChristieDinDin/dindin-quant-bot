"""
Backtest Result Cache — SQLite-backed.

Two TTL modes:
  - Nightly build (default params):  expires_hours=36  (covers weekends)
  - Manual / custom params:          expires_hours=24

Cache key = (symbol, strategy_name, params_hash)
params_hash = SHA256 of sorted JSON of {strategy_params, cash, commission}
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional


_TABLE = "backtest_cache"

_DDL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    symbol          TEXT    NOT NULL,
    strategy_name   TEXT    NOT NULL,
    params_hash     TEXT    NOT NULL,
    data_last_date  TEXT    NOT NULL,
    run_at          TEXT    NOT NULL,
    expires_at      TEXT    NOT NULL,

    return_pct      REAL,
    buy_hold_pct    REAL,
    sharpe          REAL,
    sortino         REAL,
    max_drawdown    REAL,
    win_rate        REAL,
    num_trades      INTEGER,
    avg_trade_pct   REAL,
    exposure_pct    REAL,

    result_json     TEXT,

    PRIMARY KEY (symbol, strategy_name, params_hash)
)
"""

_IDX = f"""
CREATE INDEX IF NOT EXISTS idx_bt_cache_expires
ON {_TABLE}(expires_at)
"""


def make_params_hash(strategy_params: dict, cash: float, commission: float) -> str:
    payload = json.dumps(
        {"params": strategy_params, "cash": cash, "commission": commission},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class BacktestCacheRepository:
    """Thin SQLite cache for backtest results."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self):
        with self._connect() as conn:
            conn.execute(_DDL)
            conn.execute(_IDX)
            conn.commit()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(
        self,
        symbol: str,
        strategy_name: str,
        params_hash: str,
    ) -> Optional[dict]:
        """Return cached result if it exists and has not expired. None otherwise."""
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT * FROM {_TABLE} WHERE symbol=? AND strategy_name=? "
                f"AND params_hash=? AND expires_at > ?",
                (symbol, strategy_name, params_hash, now),
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        if d.get("result_json"):
            try:
                d.update(json.loads(d["result_json"]))
            except Exception:
                pass
        return d

    def get_many(
        self,
        symbols: list[str],
        strategy_name: str,
        params_hash: str,
    ) -> dict[str, dict]:
        """Batch read. Returns {symbol: result} for all cache hits."""
        if not symbols:
            return {}
        now = datetime.utcnow().isoformat()
        placeholders = ",".join("?" * len(symbols))
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM {_TABLE} WHERE symbol IN ({placeholders}) "
                f"AND strategy_name=? AND params_hash=? AND expires_at > ?",
                (*symbols, strategy_name, params_hash, now),
            ).fetchall()
        result = {}
        for row in rows:
            d = dict(row)
            if d.get("result_json"):
                try:
                    d.update(json.loads(d["result_json"]))
                except Exception:
                    pass
            result[d["symbol"]] = d
        return result

    # ── Write ─────────────────────────────────────────────────────────────────

    def set(
        self,
        symbol: str,
        strategy_name: str,
        params_hash: str,
        result: dict[str, Any],
        data_last_date: str,
        expires_hours: int = 36,
    ) -> None:
        """Store (or replace) a backtest result."""
        now = datetime.utcnow()
        expires_at = (now + timedelta(hours=expires_hours)).isoformat()

        with self._connect() as conn:
            conn.execute(
                f"""INSERT OR REPLACE INTO {_TABLE}
                (symbol, strategy_name, params_hash, data_last_date,
                 run_at, expires_at,
                 return_pct, buy_hold_pct, sharpe, sortino, max_drawdown,
                 win_rate, num_trades, avg_trade_pct, exposure_pct, result_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    symbol, strategy_name, params_hash, data_last_date,
                    now.isoformat(), expires_at,
                    result.get("return_pct"),
                    result.get("buy_hold_return_pct"),
                    result.get("sharpe_ratio"),
                    result.get("sortino_ratio"),
                    result.get("max_drawdown_pct"),
                    result.get("win_rate_pct"),
                    result.get("num_trades"),
                    result.get("avg_trade_pct"),
                    result.get("exposure_time_pct"),
                    json.dumps(result),
                ),
            )
            conn.commit()

    def set_many(
        self,
        records: list[dict],
        expires_hours: int = 36,
    ) -> int:
        """Bulk insert. Each record: {symbol, strategy_name, params_hash, result, data_last_date}."""
        now = datetime.utcnow()
        expires_at = (now + timedelta(hours=expires_hours)).isoformat()
        rows = []
        for r in records:
            res = r["result"]
            rows.append((
                r["symbol"], r["strategy_name"], r["params_hash"], r["data_last_date"],
                now.isoformat(), expires_at,
                res.get("return_pct"), res.get("buy_hold_return_pct"),
                res.get("sharpe_ratio"), res.get("sortino_ratio"),
                res.get("max_drawdown_pct"), res.get("win_rate_pct"),
                res.get("num_trades"), res.get("avg_trade_pct"),
                res.get("exposure_time_pct"), json.dumps(res),
            ))
        with self._connect() as conn:
            conn.executemany(
                f"""INSERT OR REPLACE INTO {_TABLE}
                (symbol, strategy_name, params_hash, data_last_date,
                 run_at, expires_at,
                 return_pct, buy_hold_pct, sharpe, sortino, max_drawdown,
                 win_rate, num_trades, avg_trade_pct, exposure_pct, result_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            conn.commit()
        return len(rows)

    # ── Maintenance ───────────────────────────────────────────────────────────

    def purge_expired(self) -> int:
        """Delete expired rows. Returns count deleted."""
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                f"DELETE FROM {_TABLE} WHERE expires_at <= ?", (now,)
            )
            conn.commit()
            return cur.rowcount

    def stats(self) -> dict:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()[0]
            valid = conn.execute(
                f"SELECT COUNT(*) FROM {_TABLE} WHERE expires_at > ?", (now,)
            ).fetchone()[0]
            strategies = conn.execute(
                f"SELECT strategy_name, COUNT(*) n FROM {_TABLE} "
                f"WHERE expires_at > ? GROUP BY strategy_name", (now,)
            ).fetchall()
        return {
            "total_rows": total,
            "valid_rows": valid,
            "expired_rows": total - valid,
            "by_strategy": {r[0]: r[1] for r in strategies},
        }
