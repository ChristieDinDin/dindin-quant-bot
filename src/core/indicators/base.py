"""
Base classes for technical indicators.
All indicators should inherit from these base classes for consistency.
"""
from abc import ABC, abstractmethod
from typing import Any
import pandas as pd
import numpy as np


class Indicator(ABC):
    """
    Abstract base class for all technical indicators.
    
    This enforces a consistent interface across all indicators,
    making it easy to add new indicators and use them interchangeably.
    """
    
    def __init__(self, name: str):
        self.name = name
        self._cache = {}
    
    @abstractmethod
    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.Series:
        """
        Calculate the indicator values.
        
        Args:
            df: DataFrame with OHLCV data (columns: Open, High, Low, Close, Volume)
            **kwargs: Indicator-specific parameters
            
        Returns:
            pd.Series with indicator values
        """
        pass
    
    @abstractmethod
    def validate_params(self, **kwargs) -> bool:
        """
        Validate indicator parameters.
        
        Returns:
            True if parameters are valid, raises ValueError otherwise
        """
        pass
    
    def get_signal(self, value: float, **thresholds) -> str:
        """
        Generate trading signal based on indicator value.
        Override this method for indicator-specific logic.
        
        Returns:
            'buy', 'sell', 'hold', or custom signal type
        """
        return 'hold'
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


class MomentumIndicator(Indicator):
    """
    Base class for momentum-based indicators (RSI, MFI, Stochastic, etc.).
    These indicators typically oscillate between 0-100.
    """
    
    def __init__(self, name: str, period: int = 14, 
                 overbought: float = 70, oversold: float = 30):
        super().__init__(name)
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def get_signal(self, value: float, **thresholds) -> str:
        """
        Generate signal based on overbought/oversold levels.
        
        Args:
            value: Current indicator value
            **thresholds: Optional custom thresholds (overbought, oversold)
        """
        overbought = thresholds.get('overbought', self.overbought)
        oversold = thresholds.get('oversold', self.oversold)
        
        if value <= oversold:
            return 'buy'
        elif value >= overbought:
            return 'sell'
        else:
            return 'hold'
    
    def is_oversold(self, value: float, threshold: float = None) -> bool:
        """Check if indicator is in oversold territory."""
        threshold = threshold or self.oversold
        return value <= threshold
    
    def is_overbought(self, value: float, threshold: float = None) -> bool:
        """Check if indicator is in overbought territory."""
        threshold = threshold or self.overbought
        return value >= threshold


class TrendIndicator(Indicator):
    """
    Base class for trend-following indicators (MA, EMA, MACD, etc.).
    """
    
    def __init__(self, name: str, period: int = 20):
        super().__init__(name)
        self.period = period
    
    def get_signal(self, current_price: float, indicator_value: float) -> str:
        """
        Generate signal based on price vs indicator (e.g., price vs MA).
        """
        if current_price > indicator_value:
            return 'buy'  # Price above indicator = bullish
        elif current_price < indicator_value:
            return 'sell'  # Price below indicator = bearish
        else:
            return 'hold'


class VolatilityIndicator(Indicator):
    """
    Base class for volatility indicators (ATR, Bollinger Bands, etc.).
    """
    
    def __init__(self, name: str, period: int = 14):
        super().__init__(name)
        self.period = period
    
    @abstractmethod
    def get_bands(self, df: pd.DataFrame, **kwargs) -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        Get upper, middle, and lower bands.
        For indicators like Bollinger Bands.
        """
        pass


class VolumeIndicator(Indicator):
    """
    Base class for volume-based indicators (OBV, VWAP, etc.).
    """
    
    def __init__(self, name: str):
        super().__init__(name)
    
    def validate_volume(self, df: pd.DataFrame) -> bool:
        """Ensure volume data is present and valid."""
        if 'Volume' not in df.columns:
            raise ValueError("Volume column is required for volume indicators")
        if df['Volume'].isnull().any():
            raise ValueError("Volume data contains null values")
        return True
