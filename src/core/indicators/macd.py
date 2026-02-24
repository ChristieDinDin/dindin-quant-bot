"""
MACD (Moving Average Convergence Divergence) Indicator Implementation.

MACD is a trend-following momentum indicator that shows the relationship
between two moving averages of prices.

Components:
1. MACD Line = 12-period EMA - 26-period EMA
2. Signal Line = 9-period EMA of MACD Line
3. Histogram = MACD Line - Signal Line

Signals:
- MACD crosses above Signal: Bullish (BUY)
- MACD crosses below Signal: Bearish (SELL)
- Histogram > 0: Bullish momentum
- Histogram < 0: Bearish momentum
"""
from typing import Optional, Tuple
import pandas as pd
import numpy as np

from .base import TrendIndicator


class MACD(TrendIndicator):
    """
    MACD (Moving Average Convergence Divergence) implementation.
    
    Attributes:
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line EMA period (default: 9)
    """
    
    def __init__(self, 
                 fast_period: int = 12,
                 slow_period: int = 26,
                 signal_period: int = 9):
        super().__init__("MACD", period=slow_period)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def validate_params(self, **kwargs) -> bool:
        """Validate MACD parameters."""
        fast = kwargs.get('fast_period', self.fast_period)
        slow = kwargs.get('slow_period', self.slow_period)
        signal = kwargs.get('signal_period', self.signal_period)
        
        if not all(isinstance(p, int) and p > 0 for p in [fast, slow, signal]):
            raise ValueError("All periods must be positive integers")
        
        if fast >= slow:
            raise ValueError(f"Fast period ({fast}) must be less than slow period ({slow})")
        
        return True
    
    def calculate(self, df: pd.DataFrame, 
                  fast_period: Optional[int] = None,
                  slow_period: Optional[int] = None,
                  signal_period: Optional[int] = None) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD components.
        
        Args:
            df: DataFrame with Close column
            fast_period: Fast EMA period (optional override)
            slow_period: Slow EMA period (optional override)
            signal_period: Signal line period (optional override)
            
        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        fast = fast_period or self.fast_period
        slow = slow_period or self.slow_period
        signal = signal_period or self.signal_period
        
        self.validate_params(fast_period=fast, slow_period=slow, signal_period=signal)
        
        # Validate required columns
        if 'Close' not in df.columns:
            raise ValueError("Close column is required for MACD calculation")
        
        # Data should already be timezone-naive from DataProvider
        df = df.copy()
        
        # Calculate EMAs
        ema_fast = df['Close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['Close'].ewm(span=slow, adjust=False).mean()
        
        # MACD Line = Fast EMA - Slow EMA
        macd_line = ema_fast - ema_slow
        
        # Signal Line = EMA of MACD Line
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        
        # Histogram = MACD - Signal
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def get_signal(self, macd_value: float, signal_value: float, 
                   prev_macd: float = None, prev_signal: float = None) -> str:
        """
        Generate trading signal based on MACD crossover.
        
        Args:
            macd_value: Current MACD value
            signal_value: Current Signal value
            prev_macd: Previous MACD value (for crossover detection)
            prev_signal: Previous Signal value (for crossover detection)
            
        Returns:
            'buy', 'sell', or 'hold'
        """
        # Current position
        currently_above = macd_value > signal_value
        
        # If we have previous values, detect crossover
        if prev_macd is not None and prev_signal is not None:
            previously_above = prev_macd > prev_signal
            
            # Bullish crossover: MACD crosses above Signal
            if currently_above and not previously_above:
                return 'buy'
            
            # Bearish crossover: MACD crosses below Signal
            if not currently_above and previously_above:
                return 'sell'
        
        # No crossover, return based on current position
        if currently_above:
            return 'hold'  # Bullish but no entry signal
        else:
            return 'hold'  # Bearish but no exit signal
    
    def detect_crossover(self, macd_line: pd.Series, signal_line: pd.Series) -> pd.Series:
        """
        Detect MACD crossovers.
        
        Returns:
            pd.Series with 'bullish_cross', 'bearish_cross', or None
        """
        # Calculate differences
        diff = macd_line - signal_line
        diff_prev = diff.shift(1)
        
        # Detect crossovers
        crossover = pd.Series(None, index=macd_line.index)
        
        # Bullish crossover: diff was negative, now positive
        bullish = (diff_prev < 0) & (diff > 0)
        crossover[bullish] = 'bullish_cross'
        
        # Bearish crossover: diff was positive, now negative
        bearish = (diff_prev > 0) & (diff < 0)
        crossover[bearish] = 'bearish_cross'
        
        return crossover
    
    def calculate_with_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MACD and add all components to DataFrame.
        
        Returns:
            DataFrame with MACD_Line, MACD_Signal, MACD_Histogram, MACD_Crossover
        """
        result = df.copy()
        
        macd_line, signal_line, histogram = self.calculate(df)
        
        result['MACD_Line'] = macd_line
        result['MACD_Signal'] = signal_line
        result['MACD_Histogram'] = histogram
        result['MACD_Crossover'] = self.detect_crossover(macd_line, signal_line)
        
        return result
    
    def is_bullish(self, macd_value: float, signal_value: float) -> bool:
        """Check if MACD is in bullish configuration."""
        return macd_value > signal_value
    
    def is_bearish(self, macd_value: float, signal_value: float) -> bool:
        """Check if MACD is in bearish configuration."""
        return macd_value < signal_value
    
    def histogram_strength(self, histogram_value: float) -> str:
        """
        Assess histogram strength.
        
        Returns:
            'strong_bullish', 'bullish', 'neutral', 'bearish', 'strong_bearish'
        """
        if histogram_value > 5:
            return 'strong_bullish'
        elif histogram_value > 0:
            return 'bullish'
        elif histogram_value > -5:
            return 'bearish'
        else:
            return 'strong_bearish'
    
    def __repr__(self) -> str:
        return f"MACD(fast={self.fast_period}, slow={self.slow_period}, signal={self.signal_period})"
