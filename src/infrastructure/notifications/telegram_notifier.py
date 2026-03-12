"""
Telegram Bot notifier for Divergence Hunter trading events.

Uses only the standard `requests` library — no extra dependencies needed.

Setup (one-time, ~2 minutes):
  1. Open Telegram → search @BotFather → send /newbot → follow prompts.
     You will receive a BOT_TOKEN like:  7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  2. Open a chat with your new bot and send any message (e.g. "hi").
  3. In a browser visit:
       https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
     Copy the "id" field inside "chat" — that is your CHAT_ID.
  4. Add to your .env file:
       TELEGRAM_BOT_TOKEN=<token>
       TELEGRAM_CHAT_ID=<chat_id>

If either env var is missing, every send() call is a silent no-op, so the
rest of the application works even without notifications configured.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

EXIT_REASON_ZH = {
    "max_loss_stop":           "最大虧損停損（從進場價下跌 ≥ 7%）",
    "hard_stop":               "硬停損（跌破背離低點）",
    "trailing_stop":           "移動停利（從高點回落 5%）",
    "time_stop_20d":           "時間停損（持倉 ≥ 20 日，獲利 5–15%）",
    "time_stop_10d":           "時間停損（持倉 ≥ 10 日，獲利 ≤ 5%）",
    "bearish_div":             "頂背離賣出訊號",
    "rsi_overbought":          "RSI 超買賣出",
    "force_close_replacement": "強制平倉（更強訊號替換）",
    "manual":                  "手動平倉",
}


class TelegramNotifier:
    """
    Send Telegram messages for key trading events.

    All public methods are safe to call even when not configured — they
    silently return False instead of raising.
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> None:
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id   = chat_id   or os.getenv("TELEGRAM_CHAT_ID", "")
        self._enabled  = bool(self.bot_token and self.chat_id)

        if not self._enabled:
            logger.info(
                "TelegramNotifier: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set — "
                "notifications disabled."
            )

    # ── low-level ────────────────────────────────────────────────────────────

    def send(self, text: str) -> bool:
        """Send a plain or Markdown message. Returns True on success."""
        if not self._enabled:
            return False
        try:
            import requests  # already in stdlib-adjacent; graceful if missing

            resp = requests.post(
                _TELEGRAM_API.format(token=self.bot_token),
                json={
                    "chat_id":    self.chat_id,
                    "text":       text,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
            if not resp.ok:
                logger.warning("Telegram send failed: %s", resp.text)
            return resp.ok
        except Exception as exc:
            logger.warning("Telegram send error: %s", exc)
            return False

    # ── Stage 1 events ───────────────────────────────────────────────────────

    def notify_watchlist_added(
        self,
        symbol: str,
        yesterday_high: float,
        divergence_low: float,
        watchlist_size: int,
        max_symbols: int,
    ) -> bool:
        """
        Fired when a Stage-1 signal passes all filters and a stock is added
        to the micro-mode watchlist.
        """
        ts = datetime.now().strftime("%H:%M")
        text = (
            f"📡 *進入微觀監測*\n"
            f"股票：`{symbol}`\n"
            f"昨日高點：{yesterday_high:.2f}\n"
            f"背離低點（停損參考）：{divergence_low:.2f}\n"
            f"目前監測中：{watchlist_size}/{max_symbols} 檔\n"
            f"時間：{ts}"
        )
        return self.send(text)

    def notify_watchlist_full(
        self,
        candidate_symbol: str,
        rejected: bool,
    ) -> bool:
        """
        Fired when the watchlist is full and a new Stage-1 candidate arrives.
        `rejected=True` means the candidate was weaker than all current items.
        """
        ts = datetime.now().strftime("%H:%M")
        if rejected:
            text = (
                f"⚠️ *監測名單已滿（候選被拒）*\n"
                f"候選股票 `{candidate_symbol}` 訊號強度不足，不替換現有名單。\n"
                f"時間：{ts}"
            )
        else:
            text = (
                f"⚠️ *監測名單已滿（等待替換）*\n"
                f"候選股票 `{candidate_symbol}` 已加入等待佇列，\n"
                f"將於最弱持倉滿一日或觸發賣出時替換。\n"
                f"時間：{ts}"
            )
        return self.send(text)

    # ── Stage 2 / 3 events ───────────────────────────────────────────────────

    def notify_entry(
        self,
        symbol: str,
        entry_price: float,
        divergence_low: float,
        consecutive_bars: int,
        suggested_shares: int = 0,
        position_pct: float = 0.0,
    ) -> bool:
        """Fired when micro-mode entry condition is met (N consecutive 1-min bars).

        Uses 零股 (odd-lot) share count — suitable for any account size.
        """
        stop_pct = (entry_price - divergence_low) / entry_price * 100
        ts = datetime.now().strftime("%H:%M:%S")

        if suggested_shares > 0:
            estimated_value = suggested_shares * entry_price
            pct_label = f"{position_pct*100:.0f}%" if position_pct > 0 else ""
            shares_line = (
                f"建議：{suggested_shares} 股（零股，≈ {estimated_value:,.0f} TWD"
                + (f" / {pct_label}" if pct_label else "")
                + "）\n"
            )
        else:
            shares_line = ""

        text = (
            f"🟢 *買入訊號觸發*\n"
            f"股票：`{symbol}`\n"
            f"買入價：{entry_price:.2f}\n"
            f"硬停損：{divergence_low:.2f}（距離 {stop_pct:.1f}%）\n"
            f"最大虧損停損：{entry_price * 0.93:.2f}（-7%）\n"
            f"{shares_line}"
            f"確認：連續 {consecutive_bars} 根 1 分 K 站上昨日高點\n"
            f"時間：{ts}"
        )
        return self.send(text)

    def notify_exit(
        self,
        symbol: str,
        exit_price: float,
        entry_price: float,
        reason: str,
    ) -> bool:
        """Fired on any exit (stop, trailing, time, divergence, RSI)."""
        pnl_pct = (exit_price - entry_price) / entry_price * 100
        sign    = "+" if pnl_pct >= 0 else ""
        emoji   = "🔴" if pnl_pct < 0 else "✅"
        reason_zh = EXIT_REASON_ZH.get(reason, reason)
        ts = datetime.now().strftime("%H:%M:%S")
        text = (
            f"{emoji} *賣出執行*\n"
            f"股票：`{symbol}`\n"
            f"賣出價：{exit_price:.2f}\n"
            f"損益：{sign}{pnl_pct:.2f}%\n"
            f"原因：{reason_zh}\n"
            f"時間：{ts}"
        )
        return self.send(text)

    def notify_daily_scan_summary(
        self,
        total_scanned: int,
        new_signals: int,
        watchlist: list[str],
    ) -> bool:
        """Optional daily summary after the morning scan."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        if new_signals == 0:
            body = "今日無新買點。"
        else:
            symbols_str = "、".join(f"`{s}`" for s in watchlist)
            body = f"新進微觀名單：{symbols_str}"
        text = (
            f"📊 *每日掃描完成*\n"
            f"掃描股票：{total_scanned} 檔\n"
            f"新訊號：{new_signals} 個\n"
            f"{body}\n"
            f"時間：{ts}"
        )
        return self.send(text)

    def notify_replacement(
        self,
        outgoing: str,
        incoming: str,
        reason: str,
    ) -> bool:
        """Fired when one watchlist slot is replaced by a higher-scored candidate."""
        ts = datetime.now().strftime("%H:%M")
        text = (
            f"🔄 *監測名單替換*\n"
            f"移出：`{outgoing}`\n"
            f"移入：`{incoming}`\n"
            f"原因：{reason}\n"
            f"時間：{ts}"
        )
        return self.send(text)

    # ── test helper ──────────────────────────────────────────────────────────

    def test_connection(self) -> bool:
        """Send a test message to verify the bot is set up correctly."""
        return self.send(
            "✅ *DinDin Quant Bot* 通知系統連線成功！\n"
            "Telegram 通知已正常啟用。"
        )
