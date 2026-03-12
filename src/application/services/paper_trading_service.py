"""
Paper Trading Service — real-time strategy simulation without live order submission.

State is persisted to data/paper_trading/state.json so it survives app restarts.

Design:
  - Account starts with `initial_equity` (default 70,000 TWD).
  - Positions are opened manually via the dashboard or automatically when the
    daily scan finds a divergence signal.
  - On every refresh the service re-fetches the latest close price, marks
    peak-price for each open position, and checks all exit conditions
    (identical logic to the live IntraydayMonitor).
  - Closed trades and a timestamped equity curve are stored for charting.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Stop-loss / take-profit constants (must mirror intraday_monitor.py) ──────
MAX_LOSS_CAP        = -0.07   # -7% from entry
HARD_STOP_BUFFER    = 0.99    # divergence_low × 0.99
TRAILING_TRIGGER    = 0.15    # +15% → activate trailing
TRAILING_DROP       = 0.05    # close from peak more than 5% → exit
TIME_STOP_20D_MIN   = 0.05    # held ≥ 20d and profit ∈ [5%, 15%) → exit
TIME_STOP_20D_MAX   = 0.15
TIME_STOP_10D_MAX   = 0.05    # held ≥ 10d and profit < 5% → exit


_STATE_PATH = Path("data/paper_trading/state.json")


def _today_str() -> str:
    return date.today().isoformat()


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


class PaperTradingService:
    """
    Simulates the full Divergence Hunter trade lifecycle on paper.

    Thread-safety: not designed for concurrent writes; use inside single
    Streamlit session only.
    """

    def __init__(self, initial_equity: float = 70_000.0) -> None:
        self.initial_equity = initial_equity
        self._state: Dict[str, Any] = self._load()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load(self) -> Dict[str, Any]:
        if _STATE_PATH.exists():
            try:
                with open(_STATE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning("paper_trading state load failed: %s", exc)
        return self._blank_state()

    def _save(self) -> None:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)

    def _blank_state(self) -> Dict[str, Any]:
        return {
            "initial_equity": self.initial_equity,
            "cash": self.initial_equity,
            "open_positions": [],
            "closed_trades": [],
            "equity_curve": [
                {"date": _today_str(), "equity": self.initial_equity}
            ],
            "start_date": _today_str(),
            "last_scan_date": "",   # ISO date of most recent completed scan
            "last_scan_summary": {},
        }

    def already_scanned_today(self) -> bool:
        return self._state.get("last_scan_date", "") == _today_str()

    def get_last_scan_summary(self) -> Dict:
        return self._state.get("last_scan_summary", {})

    def reset(self) -> None:
        """Wipe all state and start fresh."""
        self._state = self._blank_state()
        self._save()

    # ── Account helpers ───────────────────────────────────────────────────────

    def get_cash(self) -> float:
        return self._state["cash"]

    def get_open_positions(self) -> List[Dict]:
        return self._state["open_positions"]

    def get_closed_trades(self) -> List[Dict]:
        return self._state["closed_trades"]

    def get_equity(self, current_prices: Optional[Dict[str, float]] = None) -> float:
        """Total equity = cash + market value of open positions."""
        equity = self._state["cash"]
        for pos in self._state["open_positions"]:
            price = (current_prices or {}).get(pos["symbol"], pos["entry_price"])
            equity += pos["shares"] * price
        return equity

    # ── Open / Close positions ────────────────────────────────────────────────

    def open_position(
        self,
        symbol: str,
        entry_price: float,
        shares: int,
        position_pct: float,
        divergence_low: float,
        signal_score: float = 0.5,
        note: str = "",
    ) -> bool:
        """
        Record a new simulated entry.

        Returns False if:
          - symbol already has an open position
          - not enough cash
        """
        if shares <= 0:
            return False
        if any(p["symbol"] == symbol for p in self._state["open_positions"]):
            logger.info("paper_trading: %s already has an open position", symbol)
            return False

        cost = shares * entry_price
        if cost > self._state["cash"]:
            logger.info(
                "paper_trading: insufficient cash %.0f for %s (need %.0f)",
                self._state["cash"], symbol, cost,
            )
            return False

        self._state["cash"] -= cost
        self._state["open_positions"].append({
            "symbol":        symbol,
            "entry_date":    _today_str(),
            "entry_price":   entry_price,
            "shares":        shares,
            "position_pct":  position_pct,
            "divergence_low": divergence_low,
            "signal_score":  signal_score,
            "peak_price":    entry_price,
            "note":          note,
        })
        self._save()
        logger.info(
            "paper_trading: opened %s × %d @ %.2f (cost %.0f TWD)",
            symbol, shares, entry_price, cost,
        )
        return True

    def close_position(
        self,
        symbol: str,
        exit_price: float,
        reason: str = "manual",
    ) -> Optional[Dict]:
        """
        Close an open position and record the trade.
        Returns the closed trade dict, or None if symbol not found.
        """
        positions = self._state["open_positions"]
        pos = next((p for p in positions if p["symbol"] == symbol), None)
        if pos is None:
            return None

        proceeds = pos["shares"] * exit_price
        self._state["cash"] += proceeds

        entry_cost = pos["shares"] * pos["entry_price"]
        pnl_twd = proceeds - entry_cost
        pnl_pct = pnl_twd / entry_cost * 100

        # Round-trip commission: 0.40% of total value (buy + sell)
        commission_twd = (entry_cost + proceeds) * 0.002
        pnl_twd -= commission_twd

        trade = {
            "symbol":       symbol,
            "entry_date":   pos["entry_date"],
            "exit_date":    _today_str(),
            "entry_price":  pos["entry_price"],
            "exit_price":   exit_price,
            "shares":       pos["shares"],
            "position_pct": pos["position_pct"],
            "signal_score": pos["signal_score"],
            "pnl_twd":      round(pnl_twd, 0),
            "pnl_pct":      round(pnl_pct, 2),
            "exit_reason":  reason,
            "exit_time":    _now_str(),
        }
        self._state["closed_trades"].append(trade)
        self._state["open_positions"] = [
            p for p in positions if p["symbol"] != symbol
        ]

        # Append today's equity snapshot
        self._state["equity_curve"].append({
            "date":   _today_str(),
            "equity": self.get_equity(),
        })
        self._save()
        logger.info(
            "paper_trading: closed %s @ %.2f  P&L %.0f TWD (%.2f%%)",
            symbol, exit_price, pnl_twd, pnl_pct,
        )
        return trade

    # ── Stop / exit logic ─────────────────────────────────────────────────────

    def _check_stop(self, pos: Dict, price: float) -> Optional[str]:
        """
        Return the exit reason string if any stop is triggered, else None.
        Mirrors the logic in IntraydayMonitor._check_exits().
        """
        entry  = pos["entry_price"]
        d_low  = pos["divergence_low"]
        peak   = pos["peak_price"]
        profit = (price - entry) / entry

        # H0: max loss cap
        if profit <= MAX_LOSS_CAP:
            return "max_loss_stop"

        # H1: hard stop (structural)
        if price <= d_low * HARD_STOP_BUFFER:
            return "hard_stop"

        # H2: trailing stop (activated once profit ≥ 15%)
        if profit >= TRAILING_TRIGGER:
            drop_from_peak = (peak - price) / peak
            if drop_from_peak >= TRAILING_DROP:
                return "trailing_stop"

        # H3: time stops
        entry_date = date.fromisoformat(pos["entry_date"])
        days_held  = (date.today() - entry_date).days
        if days_held >= 20 and TIME_STOP_20D_MIN <= profit < TIME_STOP_20D_MAX:
            return "time_stop_20d"
        if days_held >= 10 and profit < TIME_STOP_10D_MAX:
            return "time_stop_10d"

        return None

    def update_positions(
        self,
        current_prices: Dict[str, float],
    ) -> List[Dict]:
        """
        Feed current prices → update peak prices → fire stops.
        Returns list of auto-closed trade records.
        """
        auto_closed: List[Dict] = []
        to_close: List[tuple] = []

        for pos in self._state["open_positions"]:
            sym   = pos["symbol"]
            price = current_prices.get(sym)
            if price is None:
                continue

            # Update peak
            if price > pos["peak_price"]:
                pos["peak_price"] = price

            reason = self._check_stop(pos, price)
            if reason:
                to_close.append((sym, price, reason))

        for sym, price, reason in to_close:
            trade = self.close_position(sym, price, reason)
            if trade:
                auto_closed.append(trade)

        if to_close:
            self._save()

        return auto_closed

    # ── Analytics ─────────────────────────────────────────────────────────────

    def get_summary(self, current_prices: Optional[Dict[str, float]] = None) -> Dict:
        """Key portfolio metrics for the dashboard header cards."""
        current_prices = current_prices or {}
        equity         = self.get_equity(current_prices)
        initial        = self._state["initial_equity"]
        total_pnl_twd  = equity - initial
        total_pnl_pct  = total_pnl_twd / initial * 100

        trades = self._state["closed_trades"]
        winners   = [t for t in trades if t["pnl_twd"] > 0]
        losers    = [t for t in trades if t["pnl_twd"] <= 0]
        win_rate  = len(winners) / len(trades) * 100 if trades else 0.0
        avg_win   = sum(t["pnl_pct"] for t in winners) / len(winners) if winners else 0.0
        avg_loss  = sum(t["pnl_pct"] for t in losers)  / len(losers)  if losers  else 0.0
        profit_factor = (
            abs(sum(t["pnl_twd"] for t in winners)) /
            max(abs(sum(t["pnl_twd"] for t in losers)), 1)
        ) if losers else float("inf")

        # Current open P&L
        open_pnl = 0.0
        for pos in self._state["open_positions"]:
            price = current_prices.get(pos["symbol"], pos["entry_price"])
            open_pnl += (price - pos["entry_price"]) * pos["shares"]

        return {
            "initial_equity": initial,
            "current_equity": equity,
            "cash":           self._state["cash"],
            "total_pnl_twd":  total_pnl_twd,
            "total_pnl_pct":  total_pnl_pct,
            "open_pnl_twd":   open_pnl,
            "total_trades":   len(trades),
            "win_rate":       win_rate,
            "avg_win_pct":    avg_win,
            "avg_loss_pct":   avg_loss,
            "profit_factor":  profit_factor,
            "open_count":     len(self._state["open_positions"]),
            "start_date":     self._state["start_date"],
        }

    def get_equity_curve(self) -> List[Dict]:
        return self._state["equity_curve"]

    # ── Auto daily scan ───────────────────────────────────────────────────────

    def run_daily_scan(
        self,
        data_service,
        max_positions: int = 5,
        mfi_period: int = 14,
        rsi_period: int = 14,
        rsi_oversold: float = 35,
        rsi_overbought: float = 70,
        progress_cb=None,
    ) -> Dict:
        """
        Scan all DB symbols with DivergenceHunterStrategy.
        Open paper positions for fresh BUY signals.
        Update existing positions with latest prices.
        Returns a summary dict consumed by the dashboard.

        progress_cb: optional callable(current, total, symbol) for progress bars.
        """
        import pandas as pd
        from src.core.strategies.divergence_hunter import DivergenceHunterStrategy
        from src.utils.stock_list import get_available_stocks_from_db

        db_rows = get_available_stocks_from_db()
        symbols = [row[0] for row in db_rows] if db_rows else []

        strategy = DivergenceHunterStrategy(
            mfi_period=mfi_period,
            rsi_period=rsi_period,
            rsi_oversold=rsi_oversold,
            rsi_overbought=rsi_overbought,
        )

        new_entries: List[Dict] = []
        skipped_signals: List[str] = []
        errors: List[tuple] = []
        total = len(symbols)

        for i, symbol in enumerate(symbols):
            if progress_cb:
                progress_cb(i, total, symbol)
            try:
                df = data_service.get_data(symbol)
                if df is None or df.empty or len(df) < 40:
                    continue

                # initialize() writes ADX/MA20_SLOPE/RSI/MFI into df in-place
                strategy.initialize(df)
                signal = strategy.generate_signal(df)

                if signal is None or not signal.is_entry_signal:
                    continue

                # Reject if already holding this symbol
                if any(p["symbol"] == symbol for p in self._state["open_positions"]):
                    skipped_signals.append(symbol)
                    continue

                # Reject if watchlist is full
                open_count = len(self._state["open_positions"])
                if open_count >= max_positions:
                    skipped_signals.append(symbol)
                    continue

                entry_price = float(df["Close"].iloc[-1])
                divergence_low = float(
                    signal.indicators.get("divergence_low", entry_price * 0.95)
                )
                signal_score = float(signal.indicators.get("signal_score", 0.5))
                position_pct = float(signal.recommended_position_size or 0.15)

                current_equity = self.get_equity({symbol: entry_price})
                shares = max(1, int(current_equity * position_pct / entry_price))

                ok = self.open_position(
                    symbol=symbol,
                    entry_price=entry_price,
                    shares=shares,
                    position_pct=position_pct,
                    divergence_low=divergence_low,
                    signal_score=signal_score,
                    note=f"自動掃描 score={signal_score:.2f}",
                )
                if ok:
                    new_entries.append({
                        "symbol": symbol,
                        "entry_price": entry_price,
                        "shares": shares,
                        "position_pct": position_pct,
                        "signal_score": signal_score,
                        "reason": signal.reason,
                    })
            except Exception as exc:
                errors.append((symbol, str(exc)))

        # Update existing open positions with latest close prices
        open_syms = [p["symbol"] for p in self._state["open_positions"]]
        current_prices: Dict[str, float] = {}
        for sym in open_syms:
            try:
                df = data_service.get_data(sym)
                if df is not None and not df.empty:
                    current_prices[sym] = float(df["Close"].iloc[-1])
            except Exception:
                pass

        auto_exits = self.update_positions(current_prices)

        # Record today's equity snapshot
        today = _today_str()
        curve = self._state["equity_curve"]
        if not curve or curve[-1]["date"] != today:
            curve.append({"date": today, "equity": self.get_equity(current_prices)})
        else:
            curve[-1]["equity"] = self.get_equity(current_prices)
        result = {
            "scanned":     total,
            "new_entries": new_entries,
            "auto_exits":  auto_exits,
            "skipped":     skipped_signals,
            "errors":      [(s, str(e)) for s, e in errors],
            "run_at":      _now_str(),
        }
        self._state["last_scan_date"]    = _today_str()
        self._state["last_scan_summary"] = result
        self._save()

        return result
