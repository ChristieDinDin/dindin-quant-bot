"""
Moving Average Indicators (SMA and EMA).

Moving averages smooth price data to identify trends and support/resistance levels.

Types:
1. SMA (Simple Moving Average): Arithmetic mean of prices
2. EMA (Exponential Moving Average): Weighted mean, more responsive to recent prices

Common uses:
- Trend identification (price above/below MA)
- Support/resistance levels
- Crossover strategies (fast MA crosses slow MA)
"""
from typing import Optional
import pandas as pd
import numpy as np

from .base import TrendIndicator


class SimpleMovingAverage(TrendIndicator):
    """
    Simple Moving Average (SMA) implementation.
    
    SMA = Average of last N prices
    
    Attributes:
        period: Lookback period (default: 20)
    """
    
    def __init__(self, period: int = 20):
        super().__init__("SMA", period)
    
    def validate_params(self, **kwargs) -> bool:
        """Validate SMA parameters."""
        period = kwargs.get('period', self.period)
        
        if not isinstance(period, int) or period < 1:
            raise ValueError(f"Period must be a positive integer, got {period}")
        
        if period > 500:
            raise ValueError(f"Period {period} is unreasonably large (max: 500)")
        
        return True
    
    def calculate(self, df: pd.DataFrame, period: Optional[int] = None, 
                  price_column: str = 'Close') -> pd.Series:
        """
        Calculate Simple Moving Average.
        
        Args:
            df: DataFrame with price data
            period: Lookback period (optional override)
            price_column: Column to use for calculation (default: 'Close')
            
        Returns:
            pd.Series with SMA values
        """
        period = period or self.period
        self.validate_params(period=period)
        
        # Validate column exists
        if price_column not in df.columns:
            raise ValueError(f"{price_column} column not found")
        
        # Calculate SMA
        sma = df[price_column].rolling(window=period).mean()
        
        return sma
    
    def get_signal(self, current_price: float, ma_value: float) -> str:
        """
        Generate signal based on price vs MA.
        
        Returns:
            'buy' if price > MA (bullish)
            'sell' if price < MA (bearish)
            'hold' otherwise
        """
        if current_price > ma_value:
            return 'buy'  # Price above MA = uptrend
        elif current_price < ma_value:
            return 'sell'  # Price below MA = downtrend
        else:
            return 'hold'
    
    def detect_crossover(self, prices: pd.Series, ma: pd.Series) -> pd.Series:
        """
        Detect price crossovers with moving average.
        
        Returns:
            pd.Series with 'golden_cross' (bullish) or 'death_cross' (bearish)
        """
        # Price relative to MA
        above = prices > ma
        above_prev = above.shift(1)
        
        crossover = pd.Series(None, index=prices.index)
        
        # Golden cross: price crosses above MA
        crossover[~above_prev & above] = 'golden_cross'
        
        # Death cross: price crosses below MA
        crossover[above_prev & ~above] = 'death_cross'
        
        return crossover
    
    def __repr__(self) -> str:
        return f"SMA(period={self.period})"


class ExponentialMovingAverage(TrendIndicator):
    """
    Exponential Moving Average (EMA) implementation.
    
    EMA gives more weight to recent prices, making it more responsive than SMA.
    
    Attributes:
        period: Lookback period (default: 20)
    """
    
    def __init__(self, period: int = 20):
        super().__init__("EMA", period)
    
    def validate_params(self, **kwargs) -> bool:
        """Validate EMA parameters."""
        period = kwargs.get('period', self.period)
        
        if not isinstance(period, int) or period < 1:
            raise ValueError(f"Period must be a positive integer, got {period}")
        
        if period > 500:
            raise ValueError(f"Period {period} is unreasonably large (max: 500)")
        
        return True
    
    def calculate(self, df: pd.DataFrame, period: Optional[int] = None,
                  price_column: str = 'Close') -> pd.Series:
        """
        Calculate Exponential Moving Average.
        
        Args:
            df: DataFrame with price data
            period: Lookback period (optional override)
            price_column: Column to use for calculation (default: 'Close')
            
        Returns:
            pd.Series with EMA values
        """
        period = period or self.period
        self.validate_params(period=period)
        
        # Validate column exists
        if price_column not in df.columns:
            raise ValueError(f"{price_column} column not found")
        
        # Calculate EMA
        ema = df[price_column].ewm(span=period, adjust=False).mean()
        
        return ema
    
    def get_signal(self, current_price: float, ema_value: float) -> str:
        """
        Generate signal based on price vs EMA.
        
        Returns:
            'buy' if price > EMA (bullish)
            'sell' if price < EMA (bearish)
            'hold' otherwise
        """
        if current_price > ema_value:
            return 'buy'
        elif current_price < ema_value:
            return 'sell'
        else:
            return 'hold'
    
    def __repr__(self) -> str:
        return f"EMA(period={self.period})"


class MovingAverageCrossover:
    """
    Dual Moving Average Crossover Strategy Helper.
    
    Uses two MAs (fast and slow) to generate signals.
    Common combinations: 50/200, 20/50, 10/30
    """
    
    def __init__(self, fast_period: int = 50, slow_period: int = 200, 
                 ma_type: str = 'SMA'):
        """
        Initialize MA crossover.
        
        Args:
            fast_period: Fast MA period
            slow_period: Slow MA period
            ma_type: 'SMA' or 'EMA'
        """
        if fast_period >= slow_period:
            raise ValueError("Fast period must be less than slow period")
        
        self.fast_period = fast_period
        self.slow_period = slow_period
        
        if ma_type == 'SMA':
            self.fast_ma = SimpleMovingAverage(fast_period)
            self.slow_ma = SimpleMovingAverage(slow_period)
        elif ma_type == 'EMA':
            self.fast_ma = ExponentialMovingAverage(fast_period)
            self.slow_ma = ExponentialMovingAverage(slow_period)
        else:
            raise ValueError("ma_type must be 'SMA' or 'EMA'")
    
    def calculate(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        """
        Calculate both moving averages.
        
        Returns:
            Tuple of (fast_ma, slow_ma)
        """
        fast = self.fast_ma.calculate(df)
        slow = self.slow_ma.calculate(df)
        return fast, slow
    
    def detect_crossover(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect MA crossovers.
        
        Returns:
            pd.Series with 'golden_cross' (bullish) or 'death_cross' (bearish)
        """
        fast, slow = self.calculate(df)
        
        # Fast MA relative to Slow MA
        above = fast > slow
        above_prev = above.shift(1)
        
        crossover = pd.Series(None, index=df.index)
        
        # Golden cross: fast crosses above slow
        crossover[~above_prev & above] = 'golden_cross'
        
        # Death cross: fast crosses below slow
        crossover[above_prev & ~above] = 'death_cross'
        
        return crossover
    
    def get_signal(self, fast_value: float, slow_value: float,
                   prev_fast: float = None, prev_slow: float = None) -> str:
        """
        Generate trading signal based on MA crossover.
        
        Returns:
            'buy' for golden cross
            'sell' for death cross
            'hold' otherwise
        """
        currently_above = fast_value > slow_value
        
        if prev_fast is not None and prev_slow is not None:
            previously_above = prev_fast > prev_slow
            
            # Golden cross
            if currently_above and not previously_above:
                return 'buy'
            
            # Death cross
            if not currently_above and previously_above:
                return 'sell'
        
        return 'hold'
    
    def __repr__(self) -> str:
        return f"MA_Crossover(fast={self.fast_period}, slow={self.slow_period})"
