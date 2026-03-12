"""
Swing Pivot Detection — finds local highs and lows for divergence analysis.

A swing low at bar[i] is valid if:
  low[i] == min(low[i-N : i+N+1])  for some window N (default 5)

A swing high at bar[i] is valid if:
  high[i] == max(high[i-N : i+N+1])
"""
from typing import Tuple, List
import pandas as pd
import numpy as np


def find_swing_lows(
    lows: pd.Series,
    window: int = 5,
    min_bars_between: int = 8,
) -> List[Tuple[int, float]]:
    """
    Find valid swing low pivots.

    Args:
        lows: Series of low prices (index-aligned)
        window: Bars on each side for pivot validity (default 5)
        min_bars_between: Minimum bars between consecutive pivots (default 8)

    Returns:
        List of (index, value) for each swing low, oldest first
    """
    result: List[Tuple[int, float]] = []
    for i in range(window, len(lows) - window):
        if pd.isna(lows.iloc[i]):
            continue
        window_lows = lows.iloc[i - window : i + window + 1]
        if lows.iloc[i] == window_lows.min():
            if result and (i - result[-1][0]) < min_bars_between:
                if lows.iloc[i] < result[-1][1]:
                    result[-1] = (i, float(lows.iloc[i]))
                continue
            result.append((i, float(lows.iloc[i])))
    return result


def find_swing_highs(
    highs: pd.Series,
    window: int = 5,
    min_bars_between: int = 8,
) -> List[Tuple[int, float]]:
    """
    Find valid swing high pivots.

    Args:
        highs: Series of high prices
        window: Bars on each side for pivot validity
        min_bars_between: Minimum bars between consecutive pivots

    Returns:
        List of (index, value) for each swing high, oldest first
    """
    result: List[Tuple[int, float]] = []
    for i in range(window, len(highs) - window):
        if pd.isna(highs.iloc[i]):
            continue
        window_highs = highs.iloc[i - window : i + window + 1]
        if highs.iloc[i] == window_highs.max():
            if result and (i - result[-1][0]) < min_bars_between:
                if highs.iloc[i] > result[-1][1]:
                    result[-1] = (i, float(highs.iloc[i]))
                continue
            result.append((i, float(highs.iloc[i])))
    return result


def find_last_two_swing_lows(
    lows: pd.Series,
    lookback_end: int,
    window: int = 5,
    min_bars_between: int = 8,
) -> Tuple[Tuple[int, float] | None, Tuple[int, float] | None]:
    """
    Find the two most recent swing lows within [0, lookback_end].

    Returns:
        (prev_pivot, current_pivot) — prev is older, current is the latest.
        Either can be None if not found.
    """
    slice_lows = lows.iloc[: lookback_end + 1]
    pivots = find_swing_lows(slice_lows, window=window, min_bars_between=min_bars_between)
    if len(pivots) < 2:
        return (pivots[0] if len(pivots) == 1 else None, None)
    return (pivots[-2], pivots[-1])


def find_last_two_swing_highs(
    highs: pd.Series,
    lookback_end: int,
    window: int = 5,
    min_bars_between: int = 8,
) -> Tuple[Tuple[int, float] | None, Tuple[int, float] | None]:
    """Find the two most recent swing highs within [0, lookback_end]."""
    slice_highs = highs.iloc[: lookback_end + 1]
    pivots = find_swing_highs(slice_highs, window=window, min_bars_between=min_bars_between)
    if len(pivots) < 2:
        return (pivots[0] if len(pivots) == 1 else None, None)
    return (pivots[-2], pivots[-1])
