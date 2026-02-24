"""
Indicator calculation engine.
Manages multiple indicators and provides a unified interface.
"""
from typing import Dict, List, Optional
import pandas as pd

from .base import Indicator
from .mfi import MFI
from .rsi import RSI
from .macd import MACD
from .moving_average import SimpleMovingAverage, ExponentialMovingAverage


class IndicatorCalculator:
    """
    Central engine for calculating and managing multiple technical indicators.
    
    This class provides:
    - Unified interface for multiple indicators
    - Caching for performance
    - Batch calculation
    - Easy extensibility for new indicators
    """
    
    def __init__(self):
        self._indicators: Dict[str, Indicator] = {}
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def register_indicator(self, name: str, indicator: Indicator) -> None:
        """
        Register a new indicator.
        
        Args:
            name: Unique name for the indicator
            indicator: Indicator instance
        """
        if name in self._indicators:
            raise ValueError(f"Indicator '{name}' is already registered")
        
        self._indicators[name] = indicator
    
    def get_indicator(self, name: str) -> Optional[Indicator]:
        """Get an indicator by name."""
        return self._indicators.get(name)
    
    def list_indicators(self) -> List[str]:
        """Get list of registered indicator names."""
        return list(self._indicators.keys())
    
    def calculate_single(self, 
                        df: pd.DataFrame, 
                        indicator_name: str, 
                        **kwargs) -> pd.Series:
        """
        Calculate a single indicator.
        
        Args:
            df: DataFrame with OHLCV data
            indicator_name: Name of registered indicator
            **kwargs: Parameters for the indicator
            
        Returns:
            pd.Series with indicator values
        """
        indicator = self.get_indicator(indicator_name)
        if indicator is None:
            raise ValueError(f"Indicator '{indicator_name}' not found. "
                           f"Available: {self.list_indicators()}")
        
        return indicator.calculate(df, **kwargs)
    
    def calculate_all(self, 
                     df: pd.DataFrame, 
                     indicator_params: Optional[Dict[str, dict]] = None) -> pd.DataFrame:
        """
        Calculate all registered indicators.
        
        Args:
            df: DataFrame with OHLCV data
            indicator_params: Optional dict mapping indicator names to their parameters
            
        Returns:
            DataFrame with original data plus all indicator columns
        """
        result = df.copy()
        indicator_params = indicator_params or {}
        
        for name, indicator in self._indicators.items():
            params = indicator_params.get(name, {})
            try:
                result[name] = indicator.calculate(df, **params)
            except Exception as e:
                print(f"Warning: Failed to calculate {name}: {e}")
        
        return result
    
    def calculate_with_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicators and their signals.
        
        Returns:
            DataFrame with indicator values and signal columns
        """
        result = self.calculate_all(df)
        
        # Add signal columns for each indicator
        for name, indicator in self._indicators.items():
            if name in result.columns:
                signal_col = f"{name}_Signal"
                result[signal_col] = result[name].apply(
                    lambda x: indicator.get_signal(x) if pd.notna(x) else 'hold'
                )
        
        return result
    
    def clear_cache(self) -> None:
        """Clear all cached calculations."""
        self._cache.clear()
    
    def remove_indicator(self, name: str) -> None:
        """Remove an indicator from the registry."""
        if name in self._indicators:
            del self._indicators[name]
    
    def __repr__(self) -> str:
        return f"IndicatorCalculator(indicators={len(self._indicators)})"


# Factory function for common indicators
def create_default_calculator() -> IndicatorCalculator:
    """
    Create an IndicatorCalculator with commonly used indicators pre-registered.
    
    Returns:
        IndicatorCalculator with all common indicators
    """
    calculator = IndicatorCalculator()
    
    # Register MFI with default Taiwan market settings
    calculator.register_indicator('MFI', MFI(
        period=16,  # Optimized for Taiwan market
        buy_threshold=35,
        sell_threshold=85,
        strong_buy_threshold=20
    ))
    
    # Register RSI
    calculator.register_indicator('RSI', RSI(
        period=14,
        overbought=70,
        oversold=30
    ))
    
    # Register MACD
    calculator.register_indicator('MACD', MACD(
        fast_period=12,
        slow_period=26,
        signal_period=9
    ))
    
    # Register Moving Averages
    calculator.register_indicator('SMA_20', SimpleMovingAverage(period=20))
    calculator.register_indicator('SMA_50', SimpleMovingAverage(period=50))
    calculator.register_indicator('SMA_200', SimpleMovingAverage(period=200))
    calculator.register_indicator('EMA_12', ExponentialMovingAverage(period=12))
    calculator.register_indicator('EMA_26', ExponentialMovingAverage(period=26))
    
    return calculator
