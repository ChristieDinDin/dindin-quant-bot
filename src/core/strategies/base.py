"""
Base classes for trading strategies.

All trading strategies should inherit from these base classes to ensure
consistency and interoperability across the system.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

from ..models.signal import TradingSignal, SignalType, SignalStrength
from ..models.market_data import MarketDataFrame
from ..indicators.base import Indicator


class Strategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    This enforces a consistent interface making strategies:
    - Easy to test and backtest
    - Pluggable and swappable
    - Composable (combine multiple strategies)
    - Trackable (standardized metrics)
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._indicators: Dict[str, Indicator] = {}
        self._params: Dict[str, Any] = {}
        self._state: Dict[str, Any] = {}  # For stateful strategies
    
    @abstractmethod
    def initialize(self, df: pd.DataFrame) -> None:
        """
        Initialize the strategy with historical data.
        Called once before generating signals.
        
        Use this to:
        - Calculate required indicators
        - Set up initial state
        - Validate data
        """
        pass
    
    @abstractmethod
    def generate_signal(self, 
                       df: pd.DataFrame, 
                       index: int) -> Optional[TradingSignal]:
        """
        Generate a trading signal for a specific bar.
        
        Args:
            df: DataFrame with OHLCV and indicator data
            index: Index of current bar (-1 for latest)
            
        Returns:
            TradingSignal if conditions are met, None otherwise
        """
        pass
    
    @abstractmethod
    def get_position_size(self, 
                         current_equity: float,
                         current_price: float,
                         signal: TradingSignal) -> float:
        """
        Calculate position size for a signal.
        
        Args:
            current_equity: Current account equity
            current_price: Current market price
            signal: The trading signal
            
        Returns:
            Number of shares to trade
        """
        pass
    
    def add_indicator(self, name: str, indicator: Indicator) -> None:
        """Register an indicator with this strategy."""
        self._indicators[name] = indicator
    
    def get_indicator(self, name: str) -> Optional[Indicator]:
        """Get a registered indicator."""
        return self._indicators.get(name)
    
    def set_params(self, **params) -> None:
        """Set strategy parameters."""
        self._params.update(params)
    
    def get_params(self) -> Dict[str, Any]:
        """Get current strategy parameters."""
        return self._params.copy()
    
    def reset_state(self) -> None:
        """Reset strategy state. Useful for backtesting."""
        self._state.clear()
    
    @property
    def required_columns(self) -> List[str]:
        """List of required DataFrame columns."""
        return ['Open', 'High', 'Low', 'Close', 'Volume']
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate that DataFrame has required columns."""
        missing = [col for col in self.required_columns if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        return True
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


class MomentumStrategy(Strategy):
    """
    Base class for momentum-based strategies.
    
    Momentum strategies buy when indicators show oversold conditions
    and sell when overbought.
    """
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)
        self._oversold_threshold = 30
        self._overbought_threshold = 70
    
    @abstractmethod
    def get_momentum_value(self, df: pd.DataFrame, index: int) -> float:
        """Get the current momentum indicator value."""
        pass
    
    def is_oversold(self, df: pd.DataFrame, index: int) -> bool:
        """Check if momentum indicator is oversold."""
        value = self.get_momentum_value(df, index)
        return value <= self._oversold_threshold
    
    def is_overbought(self, df: pd.DataFrame, index: int) -> bool:
        """Check if momentum indicator is overbought."""
        value = self.get_momentum_value(df, index)
        return value >= self._overbought_threshold


class TrendFollowingStrategy(Strategy):
    """
    Base class for trend-following strategies.
    
    Trend strategies buy when uptrend is confirmed and sell when
    trend reverses.
    """
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)
    
    @abstractmethod
    def detect_trend(self, df: pd.DataFrame, index: int) -> str:
        """
        Detect current market trend.
        
        Returns:
            'uptrend', 'downtrend', or 'sideways'
        """
        pass
    
    def is_uptrend(self, df: pd.DataFrame, index: int) -> bool:
        """Check if market is in uptrend."""
        return self.detect_trend(df, index) == 'uptrend'
    
    def is_downtrend(self, df: pd.DataFrame, index: int) -> bool:
        """Check if market is in downtrend."""
        return self.detect_trend(df, index) == 'downtrend'


class MeanReversionStrategy(Strategy):
    """
    Base class for mean reversion strategies.
    
    Mean reversion strategies buy when price deviates too far below
    the mean and sell when it deviates too far above.
    """
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)
    
    @abstractmethod
    def calculate_mean(self, df: pd.DataFrame, index: int) -> float:
        """Calculate the mean price level."""
        pass
    
    @abstractmethod
    def calculate_deviation(self, df: pd.DataFrame, index: int) -> float:
        """Calculate how far price has deviated from mean."""
        pass
    
    def is_oversold_deviation(self, df: pd.DataFrame, index: int) -> bool:
        """Check if price is too far below mean."""
        return self.calculate_deviation(df, index) < -1.5  # -1.5 standard deviations
    
    def is_overbought_deviation(self, df: pd.DataFrame, index: int) -> bool:
        """Check if price is too far above mean."""
        return self.calculate_deviation(df, index) > 1.5  # +1.5 standard deviations


class CompositeStrategy(Strategy):
    """
    Combine multiple strategies with weighted voting.
    
    This allows you to create sophisticated strategies by combining
    simpler ones (e.g., MFI + MACD + RSI consensus).
    """
    
    def __init__(self, name: str, strategies: List[tuple[Strategy, float]]):
        """
        Args:
            name: Strategy name
            strategies: List of (strategy, weight) tuples
        """
        super().__init__(name, "Composite strategy combining multiple signals")
        self._strategies = strategies
        self._normalize_weights()
    
    def _normalize_weights(self) -> None:
        """Ensure weights sum to 1.0."""
        total = sum(weight for _, weight in self._strategies)
        self._strategies = [(s, w/total) for s, w in self._strategies]
    
    def initialize(self, df: pd.DataFrame) -> None:
        """Initialize all sub-strategies."""
        for strategy, _ in self._strategies:
            strategy.initialize(df)
    
    def generate_signal(self, df: pd.DataFrame, index: int) -> Optional[TradingSignal]:
        """
        Generate signal based on weighted combination of sub-strategies.
        """
        signals = []
        for strategy, weight in self._strategies:
            signal = strategy.generate_signal(df, index)
            if signal:
                signals.append((signal, weight))
        
        if not signals:
            return None
        
        # Calculate weighted consensus
        buy_weight = sum(w for s, w in signals if s.is_entry_signal)
        sell_weight = sum(w for s, w in signals if s.is_exit_signal)
        
        # Require >50% consensus
        if buy_weight > 0.5:
            # Use the signal from highest-weighted strategy
            primary_signal = max(
                [s for s, w in signals if s.is_entry_signal],
                key=lambda s: s.strength.value
            )
            return primary_signal
        elif sell_weight > 0.5:
            primary_signal = max(
                [s for s, w in signals if s.is_exit_signal],
                key=lambda s: s.strength.value
            )
            return primary_signal
        
        return None
    
    def get_position_size(self, current_equity: float, 
                         current_price: float, 
                         signal: TradingSignal) -> float:
        """Use the primary strategy's position sizing."""
        # Use first strategy's position sizing logic
        if self._strategies:
            primary_strategy = self._strategies[0][0]
            return primary_strategy.get_position_size(current_equity, current_price, signal)
        return 0.0
    
    def add_strategy(self, strategy: Strategy, weight: float) -> None:
        """Add a new strategy to the composite."""
        self._strategies.append((strategy, weight))
        self._normalize_weights()
