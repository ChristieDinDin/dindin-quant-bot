"""
Intraday Monitor — Stage 2/3 for Divergence Hunter micro mode.

Uses 1-min K only (no resample). Staggered polling:
- Symbols 1–4: every poll_interval_min (5 min)
- Symbol 5: every poll_interval_5th_min (6 min) — buffer for Shioaji rate limit

Entry: N consecutive 1-min bars with Close > yesterday_high.
Exits: hard stop, trailing, time stop (same logic as backtest).

Watchlist management (max 5 slots):
- When a new Stage-1 signal arrives and watchlist is full, it competes by
  signal_score against the weakest current item.
- No position on weakest  → immediate replacement.
- Position held ≥ 1 day   → force close + replace (prevents churning).
- Position held < 1 day   → new candidate enters pending_queue (max 3).
  └→ On any natural exit of the target → consume best pending candidate.
- Pending candidates expire after SIGNAL_FRESHNESS_BARS trading days (TTL).
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Optional
import threading
import time as _time
import logging
import pandas as pd

from ...infrastructure.data_providers.base import DataProvider
from ...infrastructure.notifications.telegram_notifier import TelegramNotifier
from ...utils.config import get_config

logger = logging.getLogger(__name__)

# Pending queue hard cap — protects against burst of simultaneous signals
MAX_PENDING_QUEUE = 3
# Pending candidates older than this (trading days since stage1_date) are stale
PENDING_TTL_DAYS = 8  # matches SIGNAL_FRESHNESS_BARS in divergence_hunter.py


@dataclass
class MicroWatchItem:
    """One symbol in micro mode watchlist from Stage 1."""
    symbol: str
    yesterday_high: float
    divergence_low: float
    stage1_date: date
    signal_score: float = 0.0   # higher = stronger; used for replacement priority
    position_pct: float = 0.15  # intended position size (5%–20% dynamic)


@dataclass
class MicroPosition:
    """Position opened in micro mode."""
    symbol: str
    entry_price: float
    entry_time: datetime
    divergence_low: float
    peak_price: float
    trailing_activated: bool = False


class IntradayMonitor:
    """
    Monitors up to 5 symbols in micro mode with staggered 1-min K polling.

    Rate limit: ~261 vs 270 kbars/day (S5 every 6 min).
    """

    def __init__(
        self,
        provider: DataProvider,
        *,
        max_symbols: int = 5,
        poll_interval_min: int = 5,
        poll_interval_5th_min: int = 6,
        min_consecutive_bars_above: int = 10,
        notifier: Optional[TelegramNotifier] = None,
        portfolio_equity: float = 0.0,
        position_pct: float = 0.15,
    ):
        config = get_config()
        self.provider = provider
        self.max_symbols = max_symbols or config.strategy.micro_mode_max_symbols
        self.poll_interval_min = poll_interval_min or config.strategy.poll_interval_min
        self.poll_interval_5th_min = poll_interval_5th_min or config.strategy.poll_interval_5th_min
        self.min_consecutive_bars_above = min_consecutive_bars_above or config.strategy.min_consecutive_bars_above

        # Notification — auto-init from config if not provided
        if notifier is None:
            cfg = config.notification
            notifier = TelegramNotifier(
                bot_token=cfg.telegram_bot_token,
                chat_id=cfg.telegram_chat_id,
            )
        self._notifier = notifier
        self.portfolio_equity = portfolio_equity   # updated externally before start()
        self.position_pct = position_pct

        self._watchlist: List[MicroWatchItem] = []
        self._positions: Dict[str, MicroPosition] = {}

        # Replacement queue: candidates waiting for a slot
        self._pending_queue: List[MicroWatchItem] = []          # sorted desc by score
        # Force-close map: symbol → incoming item (execute on next poll ≥ 1 day held)
        self._replacement_map: Dict[str, MicroWatchItem] = {}

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._on_entry: Optional[Callable[[str, float, float], None]] = None
        self._on_exit: Optional[Callable[[str, str], None]] = None

    # ── watchlist helpers ────────────────────────────────────────────────────

    def set_watchlist(self, items: List[MicroWatchItem]) -> None:
        """Set watchlist from Stage 1. Truncates to max_symbols."""
        self._watchlist = items[: self.max_symbols]

    def add_to_watchlist(
        self,
        symbol: str,
        yesterday_high: float,
        divergence_low: float,
        stage1_date: date,
        signal_score: float = 0.0,
        position_pct: float = 0.15,
    ) -> None:
        """
        Add a Stage-1 qualified symbol.

        If watchlist is not full: add directly.
        If full: compare signal_score against weakest current item.
          - New candidate weaker  → reject with notification.
          - No position on weakest → immediate replacement.
          - Position held ≥ 1 day  → mark for force-close, queue candidate.
          - Position held < 1 day  → queue candidate (consumed on natural exit).
        """
        # Duplicate guard — same symbol already being monitored or queued
        if any(x.symbol == symbol for x in self._watchlist):
            logger.debug("IntradayMonitor: %s already in watchlist, skipping", symbol)
            return
        if any(x.symbol == symbol for x in self._pending_queue):
            logger.debug("IntradayMonitor: %s already in pending queue, skipping", symbol)
            return

        item = MicroWatchItem(
            symbol=symbol,
            yesterday_high=yesterday_high,
            divergence_low=divergence_low,
            stage1_date=stage1_date,
            signal_score=signal_score,
            position_pct=position_pct,
        )

        if len(self._watchlist) < self.max_symbols:
            self._watchlist.append(item)
            self._notifier.notify_watchlist_added(
                symbol=symbol,
                yesterday_high=yesterday_high,
                divergence_low=divergence_low,
                watchlist_size=len(self._watchlist),
                max_symbols=self.max_symbols,
            )
            return

        # Watchlist full — find weakest
        weakest = min(self._watchlist, key=lambda x: x.signal_score)

        if item.signal_score <= weakest.signal_score:
            self._notifier.notify_watchlist_full(candidate_symbol=symbol, rejected=True)
            return

        # New candidate is stronger than weakest
        pos = self._positions.get(weakest.symbol)

        if pos is None:
            # Case B: no open position → replace immediately
            self._replace_in_watchlist(outgoing=weakest, incoming=item)
            self._notifier.notify_replacement(
                outgoing=weakest.symbol,
                incoming=symbol,
                reason="即時替換（無持倉）",
            )
            return

        # Case A: open position exists
        days_held = (date.today() - pos.entry_time.date()).days

        if days_held >= 1:
            # Case A.1: mark for force-close; consume on next poll
            self._replacement_map[weakest.symbol] = item
            self._notifier.notify_watchlist_full(candidate_symbol=symbol, rejected=False)
            logger.info(
                "IntradayMonitor: %s marked for force-close (held %d day(s)); "
                "%s queued as replacement",
                weakest.symbol, days_held, symbol,
            )
        else:
            # Case A.2: position too fresh — enqueue candidate
            self._enqueue_pending(item)
            self._notifier.notify_watchlist_full(candidate_symbol=symbol, rejected=False)

    def set_callbacks(
        self,
        on_entry: Optional[Callable[[str, float, float], None]] = None,
        on_exit: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """Set entry/exit callbacks. on_entry(symbol, price, divergence_low); on_exit(symbol, reason)."""
        self._on_entry = on_entry
        self._on_exit = on_exit

    # ── pending queue helpers ────────────────────────────────────────────────

    def _enqueue_pending(self, item: MicroWatchItem) -> None:
        """Add candidate to pending queue, keep only best MAX_PENDING_QUEUE items."""
        self._pending_queue.append(item)
        self._pending_queue.sort(key=lambda x: x.signal_score, reverse=True)
        if len(self._pending_queue) > MAX_PENDING_QUEUE:
            dropped = self._pending_queue.pop()  # remove lowest-scored
            logger.info(
                "IntradayMonitor: pending queue full; dropped %s (score=%.2f)",
                dropped.symbol, dropped.signal_score,
            )

    def _purge_stale_pending(self) -> None:
        """Remove pending candidates whose Stage-1 signal is older than PENDING_TTL_DAYS."""
        today = date.today()
        fresh = [
            item for item in self._pending_queue
            if (today - item.stage1_date).days <= PENDING_TTL_DAYS
        ]
        stale_count = len(self._pending_queue) - len(fresh)
        if stale_count:
            logger.info("IntradayMonitor: purged %d stale pending candidate(s)", stale_count)
        self._pending_queue = fresh

    def _try_consume_pending(self, freed_symbol: str) -> None:
        """
        Called after any slot opens (natural exit or force-close).
        Removes the freed symbol from watchlist and brings in the best pending candidate.
        """
        self._purge_stale_pending()
        # Remove freed slot
        self._watchlist = [x for x in self._watchlist if x.symbol != freed_symbol]
        # Also clean up replacement map if freed naturally
        self._replacement_map.pop(freed_symbol, None)

        if not self._pending_queue:
            return

        incoming = self._pending_queue.pop(0)  # highest scored
        self._watchlist.append(incoming)
        self._notifier.notify_watchlist_added(
            symbol=incoming.symbol,
            yesterday_high=incoming.yesterday_high,
            divergence_low=incoming.divergence_low,
            watchlist_size=len(self._watchlist),
            max_symbols=self.max_symbols,
        )
        logger.info(
            "IntradayMonitor: %s consumed from pending queue (score=%.2f)",
            incoming.symbol, incoming.signal_score,
        )

    def _replace_in_watchlist(self, outgoing: MicroWatchItem, incoming: MicroWatchItem) -> None:
        """Swap outgoing for incoming in watchlist in-place."""
        self._watchlist = [x for x in self._watchlist if x.symbol != outgoing.symbol]
        self._watchlist.append(incoming)

    # ── polling ──────────────────────────────────────────────────────────────

    def _get_intraday(self, symbol: str, target_date: date) -> pd.DataFrame:
        """Fetch 1-min K for the day. Requires provider.get_intraday_1min."""
        if not hasattr(self.provider, "get_intraday_1min"):
            return pd.DataFrame()
        return self.provider.get_intraday_1min(symbol=symbol, target_date=target_date)

    def _check_entry(self, df: pd.DataFrame, item: MicroWatchItem) -> bool:
        """True if last N bars all have Close > yesterday_high."""
        if df.empty or len(df) < self.min_consecutive_bars_above:
            return False
        last = df.tail(self.min_consecutive_bars_above)
        return bool((last["Close"] > item.yesterday_high).all())

    def _check_exits(self, df: pd.DataFrame, pos: MicroPosition) -> Optional[str]:
        """Returns exit reason if any, else None."""
        if df.empty:
            return None
        close = float(df["Close"].iloc[-1])
        high = float(df["High"].iloc[-1])

        # Update peak
        pos.peak_price = max(pos.peak_price, high, close)
        profit_pct = (close - pos.entry_price) / pos.entry_price

        if profit_pct > 0.15:
            pos.trailing_activated = True

        # H0: Max loss cap — never lose more than 7% from entry
        if profit_pct <= -0.07:
            return "max_loss_stop"

        # H1: Hard stop — price breaks below divergence low (with 1% buffer)
        if close < pos.divergence_low * 0.99:
            return "hard_stop"

        # H2: Trailing stop
        if pos.trailing_activated:
            drop_pct = (pos.peak_price - close) / pos.peak_price
            if drop_pct >= 0.05:
                return "trailing_stop"

        # H3/H4: Time stop (using calendar days)
        current_dt = df.index[-1]
        current_date = current_dt.date() if hasattr(current_dt, "date") else date.today()
        entry_date = pos.entry_time.date() if hasattr(pos.entry_time, "date") else pos.entry_time
        delta = current_date - entry_date
        days_held = delta.days if isinstance(delta, timedelta) else int(delta)

        if 0.05 < profit_pct <= 0.15 and days_held >= 20:
            return "time_stop_20d"
        if profit_pct <= 0.05 and days_held >= 10:
            return "time_stop_10d"

        return None

    def poll_symbol(self, item: MicroWatchItem, target_date: date) -> None:
        """Fetch 1-min K, check entry or exits for one symbol."""
        symbol = item.symbol
        df = self._get_intraday(symbol, target_date)
        if df.empty:
            return

        pos = self._positions.get(symbol)

        if pos is None:
            # ── no position: check forced replacement or entry ────────────
            if symbol in self._replacement_map:
                # Slot was marked for force-close but position already gone —
                # replace immediately (e.g., position was never entered)
                incoming = self._replacement_map.pop(symbol)
                self._replace_in_watchlist(outgoing=item, incoming=incoming)
                self._notifier.notify_replacement(
                    outgoing=symbol,
                    incoming=incoming.symbol,
                    reason="即時替換（等待期間未進場）",
                )
                return

            if self._check_entry(df, item):
                price = float(df["Close"].iloc[-1])
                pos = MicroPosition(
                    symbol=symbol,
                    entry_price=price,
                    entry_time=datetime.now(),
                    divergence_low=item.divergence_low,
                    peak_price=price,
                )
                self._positions[symbol] = pos
                # Position sizing: use signal-specific pct (5%–20%),
                # fall back to monitor default if item has no score yet.
                effective_pct = item.position_pct if item.position_pct > 0 else self.position_pct
                # Zero-share (零股) calculation — works for any account size.
                # 1 lot = 1,000 shares; for small accounts (<100K TWD) use shares directly.
                suggested_shares = 0
                if self.portfolio_equity > 0:
                    position_value = self.portfolio_equity * effective_pct
                    suggested_shares = max(1, int(position_value / price))
                self._notifier.notify_entry(
                    symbol=symbol,
                    entry_price=price,
                    divergence_low=item.divergence_low,
                    consecutive_bars=self.min_consecutive_bars_above,
                    suggested_shares=suggested_shares,
                    position_pct=effective_pct,
                )
                if self._on_entry:
                    self._on_entry(symbol, price, item.divergence_low)

        else:
            # ── has position: check force-close first ────────────────────
            if symbol in self._replacement_map:
                days_held = (date.today() - pos.entry_time.date()).days
                if days_held >= 1:
                    exit_price = float(df["Close"].iloc[-1])
                    self._notifier.notify_exit(
                        symbol=symbol,
                        exit_price=exit_price,
                        entry_price=pos.entry_price,
                        reason="force_close_replacement",
                    )
                    incoming = self._replacement_map[symbol]
                    self._notifier.notify_replacement(
                        outgoing=symbol,
                        incoming=incoming.symbol,
                        reason=f"強制平倉替換（持倉 {days_held} 天）",
                    )
                    del self._positions[symbol]
                    self._try_consume_pending(symbol)  # removes outgoing, adds incoming
                    # incoming was already in replacement_map; _try_consume_pending
                    # won't find it in pending_queue, so add it manually if queue empty
                    if not any(x.symbol == incoming.symbol for x in self._watchlist):
                        self._watchlist.append(incoming)
                    if self._on_exit:
                        self._on_exit(symbol, "force_close_replacement")
                    return
                # < 1 day held: wait — will check again next poll

            # ── normal exit checks ───────────────────────────────────────
            reason = self._check_exits(df, pos)
            if reason:
                exit_price = float(df["Close"].iloc[-1])
                self._notifier.notify_exit(
                    symbol=symbol,
                    exit_price=exit_price,
                    entry_price=pos.entry_price,
                    reason=reason,
                )
                del self._positions[symbol]
                # Consume best pending candidate into this freed slot
                self._try_consume_pending(symbol)
                if self._on_exit:
                    self._on_exit(symbol, reason)

    @staticmethod
    def _is_trading_day(d: date) -> bool:
        """
        Returns True if d is Mon–Fri (weekday).
        Public holidays return empty data from Shioaji, handled gracefully downstream.
        """
        return d.weekday() < 5  # 5=Sat, 6=Sun

    def _run_loop(self) -> None:
        """Main loop: staggered polling."""
        today = date.today()

        if not self._is_trading_day(today):
            logger.info("IntradayMonitor: %s is not a trading day — skipping poll loop", today)
            return

        # Build two schedules: A = symbols 1..min(4,n), B = symbol 5 if n==5
        track_a = self._watchlist[: min(4, len(self._watchlist))]
        track_b = self._watchlist[4:5]  # 5th symbol only

        t0 = _time.monotonic()
        next_a = t0
        next_b = t0

        while not self._stop_event.is_set():
            now = _time.monotonic()

            if now >= next_a:
                for item in list(track_a):  # copy: watchlist may change during loop
                    try:
                        self.poll_symbol(item, today)
                    except Exception as e:
                        logger.error("IntradayMonitor poll error (%s): %s", item.symbol, e)
                next_a = now + self.poll_interval_min * 60

            if track_b and now >= next_b:
                try:
                    self.poll_symbol(track_b[0], today)
                except Exception as e:
                    logger.error("IntradayMonitor poll error (%s): %s", track_b[0].symbol, e)
                next_b = now + self.poll_interval_5th_min * 60

            self._stop_event.wait(60)  # Sleep 1 min, recheck stop

    def start(self) -> None:
        """Start background polling thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop polling."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None

    # ── read-only status ─────────────────────────────────────────────────────

    @property
    def watchlist(self) -> List[MicroWatchItem]:
        return list(self._watchlist)

    @property
    def positions(self) -> Dict[str, MicroPosition]:
        return dict(self._positions)

    @property
    def pending_queue(self) -> List[MicroWatchItem]:
        return list(self._pending_queue)
