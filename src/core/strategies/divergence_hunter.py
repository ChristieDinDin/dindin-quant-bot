"""
Divergence Hunter — B-Tier 死水盤整期 暗池吸血流

Bullish divergence: price lower low + MFI higher low (hidden accumulation)
Bearish divergence: price higher high + MFI lower high (distribution)
Right-side confirmation: Close > prior High before entry
RSI as filter only: oversold for buy gate, overbought for sell exit.
"""
from typing import Optional
from datetime import datetime
from decimal import Decimal
import pandas as pd
import numpy as np

try:
    import pandas_ta as _pta
except ImportError:
    _pta = None

from .base import Strategy
from ..models.signal import TradingSignal, SignalType, SignalStrength
from ..indicators.rsi import RSI
from ..indicators.mfi import MFI
from ..indicators.pivot import find_last_two_swing_lows, find_last_two_swing_highs

# ── Hardcoded backend logic (not exposed in UI) ─────────────────────────────
SWING_PIVOT_WINDOW = 5
MIN_BARS_BETWEEN_PIVOTS = 8
LOOKBACK_WINDOW = 30
SIGNAL_FRESHNESS_BARS = 8

# ── Regime filter (consolidation gate) ──────────────────────────────────────
REGIME_ADX_PERIOD    = 14
REGIME_ADX_MAX       = 30    # ADX must be BELOW this; ≥30 = trending → skip
REGIME_MA_PERIOD     = 20    # 20-day MA
REGIME_MA_LOOKBACK   = 10    # slope window: compare MA[now] vs MA[10 bars ago]
REGIME_MA_SLOPE_MAX  = 0.05  # |slope| must be < 5% to be considered flat

# ── Liquidity filter (MFI integrity gate) ───────────────────────────────────
LIQUIDITY_LOOKBACK   = 20    # rolling window for average daily trading value
LIQUIDITY_MIN_TWD    = 10_000_000  # 10M TWD/day minimum (value = Close × Volume)

# ── Dynamic position sizing ───────────────────────────────────────────────────
MIN_POSITION_PCT = 0.05   # weakest signal → 5% of equity
MAX_POSITION_PCT = 0.20   # strongest signal → 20% of equity


def _compute_signal_score(
    rsi_at_div: float,
    rsi_oversold: float,
    curr_mfi: float,
    prev_mfi: float,
    curr_low: float,
    prev_low: float,
) -> float:
    """
    Score 0.0–1.0 measuring divergence strength. Used for:
      - Dynamic position sizing (5%–20%)
      - Watchlist replacement priority

    Components:
      RSI depth    (40%): how far RSI is below the oversold threshold
      MFI strength (40%): absolute improvement from prev_mfi → curr_mfi
      Price depth  (20%): relative depth of the lower low (capped at 20%)
    """
    rsi_depth = max(0.0, min(1.0, (rsi_oversold - rsi_at_div) / rsi_oversold))
    mfi_strength = max(0.0, min(1.0, (curr_mfi - prev_mfi) / 50.0))
    price_depth = (
        max(0.0, min(1.0, (prev_low - curr_low) / prev_low / 0.20))
        if prev_low > 0 else 0.0
    )
    return rsi_depth * 0.4 + mfi_strength * 0.4 + price_depth * 0.2


class DivergenceHunterStrategy(Strategy):
    """
    Divergence-based strategy for consolidation markets.

    BUY: Bullish divergence + RSI oversold + Right-side confirmation
    SELL: Bearish divergence OR RSI overbought
    """

    def __init__(
        self,
        mfi_period: int = 14,
        rsi_period: int = 14,
        rsi_oversold: float = 35,
        rsi_overbought: float = 70,
        position_pct: float = 0.15,
        use_rsi_sell: bool = True,
    ):
        super().__init__(
            name="Divergence Hunter",
            description="底背離 + 右側確認機制 — 盤整期暗池吸血流",
        )
        self.mfi_period = mfi_period
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.use_rsi_sell = use_rsi_sell
        self.position_pct = position_pct

        self.rsi_indicator = RSI(
            period=rsi_period,
            overbought=rsi_overbought,
            oversold=rsi_oversold,
        )
        self.mfi_indicator = MFI(period=mfi_period)

        self._state["rsi_values"] = None
        self._state["mfi_values"] = None
        self._state["last_bull_div_bar"] = None   # bar index when bullish div was detected
        self._state["last_bear_div_bar"] = None

    def initialize(self, df: pd.DataFrame) -> None:
        self.validate_data(df)
        self._state["rsi_values"] = self.rsi_indicator.calculate(df)
        self._state["mfi_values"] = self.mfi_indicator.calculate(df)
        self._state["last_bull_div_bar"] = None
        self._state["last_bear_div_bar"] = None

        if "RSI" not in df.columns:
            df["RSI"] = self._state["rsi_values"]
        if "MFI" not in df.columns:
            df["MFI"] = self._state["mfi_values"]

        # ── Regime filter indicators ─────────────────────────────────────────
        # ADX: measures trend strength (direction-neutral). Low ADX = range-bound.
        if _pta is not None:
            try:
                adx_result = _pta.adx(
                    df["High"], df["Low"], df["Close"], length=REGIME_ADX_PERIOD
                )
                adx_col = f"ADX_{REGIME_ADX_PERIOD}"
                adx_values = (
                    adx_result[adx_col]
                    if adx_result is not None and adx_col in adx_result.columns
                    else pd.Series(np.nan, index=df.index)
                )
            except Exception:
                adx_values = pd.Series(np.nan, index=df.index)
        else:
            adx_values = pd.Series(np.nan, index=df.index)

        # MA20 slope: |change over 10 bars| / base. Flat MA = no trend.
        ma20 = df["Close"].rolling(REGIME_MA_PERIOD).mean()
        ma20_base = ma20.shift(REGIME_MA_LOOKBACK).replace(0, np.nan)
        ma20_slope = (ma20 - ma20_base) / ma20_base

        self._state["adx_values"] = adx_values
        self._state["ma20_slope_values"] = ma20_slope

        if "ADX" not in df.columns:
            df["ADX"] = adx_values
        if "MA20_SLOPE" not in df.columns:
            df["MA20_SLOPE"] = ma20_slope

    def generate_signal(self, df: pd.DataFrame, index: int = -1) -> Optional[TradingSignal]:
        """
        Generate signal. index=-1 means latest bar.
        In backtest, df is the full history up to current bar.
        """
        if "RSI" not in df.columns or "MFI" not in df.columns:
            self.initialize(df)

        n = len(df)
        if n < LOOKBACK_WINDOW + SWING_PIVOT_WINDOW * 2:
            return None

        # Use iloc for index — -1 means last row
        bar_idx = n + index if index < 0 else index
        if bar_idx < LOOKBACK_WINDOW + SWING_PIVOT_WINDOW:
            return None

        slice_df = df.iloc[: bar_idx + 1]
        lows = slice_df["Low"]
        highs = slice_df["High"]
        mfi = slice_df["MFI"]
        rsi = slice_df["RSI"]

        current_rsi = rsi.iloc[-1]
        current_mfi = mfi.iloc[-1]
        current_price = slice_df["Close"].iloc[-1]
        current_high = slice_df["High"].iloc[-1]
        prev_high = slice_df["High"].iloc[-2] if len(slice_df) >= 2 else current_high

        if isinstance(slice_df.index, pd.DatetimeIndex):
            current_time = slice_df.index[-1]
            if hasattr(current_time, "tz") and current_time.tz is not None:
                current_time = current_time.tz_localize(None)
            current_time = (
                current_time.to_pydatetime()
                if hasattr(current_time, "to_pydatetime")
                else current_time
            )
        else:
            current_time = datetime.now()

        if pd.isna(current_rsi) or pd.isna(current_mfi):
            return None

        symbol = getattr(df, "symbol", "UNKNOWN")

        # ── SELL: Bearish divergence OR RSI overbought ────────────────────────
        prev_high_pivot, curr_high_pivot = find_last_two_swing_highs(
            highs, lookback_end=len(slice_df) - 1,
            window=SWING_PIVOT_WINDOW,
            min_bars_between=MIN_BARS_BETWEEN_PIVOTS,
        )

        if prev_high_pivot and curr_high_pivot:
            prev_h_idx, prev_h_val = prev_high_pivot
            curr_h_idx, curr_h_val = curr_high_pivot
            prev_mfi = mfi.iloc[prev_h_idx]
            curr_mfi = mfi.iloc[curr_h_idx]
            if (
                curr_h_val > prev_h_val
                and curr_mfi < prev_mfi
                and not pd.isna(prev_mfi)
                and not pd.isna(curr_mfi)
            ):
                return TradingSignal(
                    timestamp=current_time,
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.STRONG,
                    price=Decimal(str(current_price)),
                    strategy_name=self.name,
                    reason=f"頂背離: 價創高 MFI未跟 (賣出)",
                    recommended_position_size=Decimal("0"),
                    indicators={"RSI": current_rsi, "MFI": current_mfi},
                )

        if self.use_rsi_sell and current_rsi >= self.rsi_overbought:
            return TradingSignal(
                timestamp=current_time,
                symbol=symbol,
                signal_type=SignalType.SELL,
                strength=SignalStrength.MODERATE,
                price=Decimal(str(current_price)),
                strategy_name=self.name,
                reason=f"RSI 超買 {current_rsi:.1f} >= {self.rsi_overbought}",
                recommended_position_size=Decimal("0"),
                indicators={"RSI": current_rsi, "MFI": current_mfi},
            )

        # ── BUY: Bullish divergence + RSI oversold + Right-side confirmation ──
        prev_low_pivot, curr_low_pivot = find_last_two_swing_lows(
            lows, lookback_end=len(slice_df) - 1,
            window=SWING_PIVOT_WINDOW,
            min_bars_between=MIN_BARS_BETWEEN_PIVOTS,
        )

        if not (prev_low_pivot and curr_low_pivot):
            return None

        prev_idx, prev_low_val = prev_low_pivot
        curr_idx, curr_low_val = curr_low_pivot
        prev_mfi_val = mfi.iloc[prev_idx]
        curr_mfi_val = mfi.iloc[curr_idx]

        if pd.isna(prev_mfi_val) or pd.isna(curr_mfi_val):
            return None

        # Bullish divergence: price lower low, MFI higher low
        bullish_div = curr_low_val < prev_low_val and curr_mfi_val > prev_mfi_val

        if not bullish_div:
            return None

        # Freshness: divergence bar within last SIGNAL_FRESHNESS_BARS
        bars_since_div = (len(slice_df) - 1) - curr_idx
        if bars_since_div > SIGNAL_FRESHNESS_BARS:
            return None

        # RSI gate — check at divergence bar (背離當下), NOT confirmation bar
        rsi_at_div_bar = rsi.iloc[curr_idx]
        if pd.isna(rsi_at_div_bar) or rsi_at_div_bar >= self.rsi_oversold:
            return None

        # Right-side confirmation: Close[today] > High[yesterday]
        close_today = slice_df["Close"].iloc[-1]
        high_yesterday = slice_df["High"].iloc[-2] if len(slice_df) >= 2 else 0
        if close_today <= high_yesterday:
            return None

        # ── Regime filter: block entry during trending markets ────────────────
        # ADX ≥ 30 → strong trend (up or down) → skip
        adx_now = slice_df["ADX"].iloc[-1] if "ADX" in slice_df.columns else np.nan
        if not pd.isna(adx_now) and adx_now >= REGIME_ADX_MAX:
            return None

        # |MA20 slope| ≥ 5% over 10 bars → directional drift → skip
        ma_slope_now = (
            slice_df["MA20_SLOPE"].iloc[-1]
            if "MA20_SLOPE" in slice_df.columns
            else np.nan
        )
        if not pd.isna(ma_slope_now) and abs(ma_slope_now) >= REGIME_MA_SLOPE_MAX:
            return None

        # ── Liquidity filter: MFI integrity gate ─────────────────────────────
        # Low-volume stocks produce fake MFI divergence (single trade dominates).
        # 20-day avg daily traded value (Close × Volume) must exceed 10M TWD.
        if "Close" in slice_df.columns and "Volume" in slice_df.columns:
            daily_value = slice_df["Close"] * slice_df["Volume"]
            avg_value = daily_value.rolling(LIQUIDITY_LOOKBACK).mean().iloc[-1]
            if not pd.isna(avg_value) and avg_value < LIQUIDITY_MIN_TWD:
                return None

        # ── Dynamic position sizing based on signal strength ──────────────────
        signal_score = _compute_signal_score(
            rsi_at_div=rsi_at_div_bar,
            rsi_oversold=self.rsi_oversold,
            curr_mfi=curr_mfi_val,
            prev_mfi=prev_mfi_val,
            curr_low=curr_low_val,
            prev_low=prev_low_val,
        )
        position_pct = round(
            MIN_POSITION_PCT + signal_score * (MAX_POSITION_PCT - MIN_POSITION_PCT),
            4,
        )

        return TradingSignal(
            timestamp=current_time,
            symbol=symbol,
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            price=Decimal(str(current_price)),
            strategy_name=self.name,
            reason=f"底背離+右側確認 (RSI={rsi_at_div_bar:.1f}, score={signal_score:.2f}, pos={position_pct*100:.0f}%)",
            recommended_position_size=Decimal(str(position_pct)),
            indicators={
                "RSI_div_bar": rsi_at_div_bar,
                "RSI_now": current_rsi,
                "MFI": current_mfi,
                "divergence_low": curr_low_val,  # for hard stop in backtest
                "signal_score": signal_score,    # for watchlist priority + position sizing
            },
        )

    def get_position_size(
        self,
        current_equity: float,
        current_price: float,
        signal: TradingSignal,
    ) -> float:
        if signal.signal_type in [SignalType.SELL, SignalType.CLOSE]:
            return 0
        position_value = current_equity * float(signal.recommended_position_size)
        shares = int(position_value / current_price)
        shares = (shares // 1000) * 1000
        return max(shares, 0)
