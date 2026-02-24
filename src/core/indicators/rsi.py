"""
Relative Strength Index (RSI) Indicator Implementation.

RSI is a momentum oscillator that measures the speed and magnitude of price changes.
It oscillates between 0 and 100, typically using a 14-period lookback.

Formula:
1. Calculate price changes (gains and losses)
2. Average Gain = Average of gains over period
3. Average Loss = Average of losses over period
4. RS = Average Gain / Average Loss
5. RSI = 100 - (100 / (1 + RS))

Range: 0-100
- RSI < 30: Oversold (potential BUY)
- RSI > 70: Overbought (potential SELL)
- RSI = 50: Neutral/equilibrium
"""
from typing import Optional
import pandas as pd
import numpy as np

from .base import MomentumIndicator


class RSI(MomentumIndicator):
    """
    Relative Strength Index (RSI) implementation.
    
    Attributes:
        period: Lookback period for RSI calculation (default: 14)
        overbought: Level considered overbought (default: 70)
        oversold: Level considered oversold (default: 30)
    """
    
    def __init__(self, 
                 period: int = 14,
                 overbought: float = 70,
                 oversold: float = 30):
        super().__init__("RSI", period, overbought, oversold)
    
    def validate_params(self, **kwargs) -> bool:
        """Validate RSI parameters."""
        period = kwargs.get('period', self.period)
        
        if not isinstance(period, int) or period < 1:
            raise ValueError(f"Period must be a positive integer, got {period}")
        
        if period > 100:
            raise ValueError(f"Period {period} is unreasonably large (max: 100)")
        
        return True
    
    def calculate(self, df: pd.DataFrame, period: Optional[int] = None) -> pd.Series:
        """
        Calculate Relative Strength Index.
        
        Args:
            df: DataFrame with Close column
            period: Lookback period (overrides instance period if provided)
            
        Returns:
            pd.Series with RSI values
        """
        period = period or self.period
        self.validate_params(period=period)
        
        # Validate required columns
        if 'Close' not in df.columns:
            raise ValueError("Close column is required for RSI calculation")
        
        # Data should already be timezone-naive from DataProvider
        df = df.copy()
        
        if len(df) < period + 1:
            return pd.Series(np.nan, index=df.index, dtype='float64')
        
        # Calculate price changes
        delta = df['Close'].diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)
        
        # Calculate exponential moving averages of gains and losses
        # Using Wilder's smoothing (same as EMA with alpha = 1/period)
        avg_gains = gains.ewm(com=period - 1, min_periods=period).mean()
        avg_losses = losses.ewm(com=period - 1, min_periods=period).mean()
        
        # Calculate RS (Relative Strength)
        rs = avg_gains / avg_losses
        
        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))
        
        # Handle edge cases
        rsi = rsi.fillna(50)  # Neutral when no data
        
        return rsi
    
    def get_signal(self, value: float, **thresholds) -> str:
        """
        Generate trading signal based on RSI value.
        
        Returns:
            'buy', 'sell', or 'hold'
        """
        oversold = thresholds.get('oversold', self.oversold)
        overbought = thresholds.get('overbought', self.overbought)
        
        if value <= oversold:
            return 'buy'
        elif value >= overbought:
            return 'sell'
        else:
            return 'hold'
    
    def get_divergence(self, df: pd.DataFrame, rsi: pd.Series = None, 
                      lookback: int = 5) -> pd.Series:
        """
        Detect bullish/bearish divergence between price and RSI.
        
        Bullish divergence: Price makes lower low, but RSI makes higher low
        Bearish divergence: Price makes higher high, but RSI makes lower high
        
        Args:
            df: DataFrame with price data
            rsi: Pre-calculated RSI values (optional)
            lookback: Number of periods to look back for divergence
            
        Returns:
            pd.Series with 'bullish', 'bearish', or None
        """
        if rsi is None:
            rsi = self.calculate(df)
        
        divergence = pd.Series(None, index=df.index)
        
        # Simplified divergence detection
        # TODO: Implement sophisticated peak/trough detection
        
        return divergence
    
    def is_extreme_oversold(self, value: float, threshold: float = 20) -> bool:
        """Check if RSI is in extreme oversold territory."""
        return value <= threshold
    
    def is_extreme_overbought(self, value: float, threshold: float = 80) -> bool:
        """Check if RSI is in extreme overbought territory."""
        return value >= threshold
    
    def calculate_with_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate RSI and add signal metadata.
        
        Returns:
            DataFrame with additional columns: RSI, RSI_Signal
        """
        result = df.copy()
        result['RSI'] = self.calculate(df)
        result['RSI_Signal'] = result['RSI'].apply(self.get_signal)
        
        return result
    
    def __repr__(self) -> str:
        return f"RSI(period={self.period}, oversold={self.oversold}, overbought={self.overbought})"
