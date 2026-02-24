"""
MFI Hunter Strategy Implementation.

This is a momentum-based strategy using the Money Flow Index (MFI) indicator
to identify oversold and overbought conditions with tiered position sizing.

Strategy Rules:
1. BUY when MFI < buy_threshold (default: 35)
   - Normal position: 15% of equity
   
2. STRONG BUY when MFI < strong_buy_threshold (default: 20)
   - Larger position: 30% of equity
   
3. SELL when MFI > sell_threshold (default: 85)
   - Close all positions

Position Management:
- Maximum total position: 80% of equity
- Tiered entries allow averaging down in strong opportunities
"""
from typing import Optional
from datetime import datetime
from decimal import Decimal
import pandas as pd

from .base import MomentumStrategy
from ..models.signal import TradingSignal, SignalType, SignalStrength
from ..indicators.mfi import MFI


class MfiHunterStrategy(MomentumStrategy):
    """
    MFI-based trading strategy optimized for Taiwan stock market.
    
    Features:
    - Tiered position sizing based on MFI levels
    - Risk management with max position limits
    - Clear entry/exit rules
    """
    
    def __init__(self,
                 mfi_period: int = 16,
                 buy_threshold: float = 35,
                 sell_threshold: float = 85,
                 strong_buy_threshold: float = 20,
                 max_position_pct: float = 0.80,
                 normal_position_pct: float = 0.15,
                 strong_position_pct: float = 0.30):
        """
        Initialize MFI Hunter strategy.
        
        Args:
            mfi_period: MFI calculation period (default: 16)
            buy_threshold: MFI level for normal buy (default: 35)
            sell_threshold: MFI level for sell (default: 85)
            strong_buy_threshold: MFI level for strong buy (default: 20)
            max_position_pct: Maximum total position size (default: 0.80)
            normal_position_pct: Position size for normal buy (default: 0.15)
            strong_position_pct: Position size for strong buy (default: 0.30)
        """
        super().__init__(
            name="MFI Hunter",
            description="Tiered momentum strategy using Money Flow Index"
        )
        
        # Strategy parameters
        self.mfi_period = mfi_period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.strong_buy_threshold = strong_buy_threshold
        self.max_position_pct = max_position_pct
        self.normal_position_pct = normal_position_pct
        self.strong_position_pct = strong_position_pct
        
        # Initialize MFI indicator
        self.mfi_indicator = MFI(
            period=mfi_period,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            strong_buy_threshold=strong_buy_threshold
        )
        self.add_indicator('MFI', self.mfi_indicator)
        
        # Update momentum thresholds
        self._oversold_threshold = buy_threshold
        self._overbought_threshold = sell_threshold
        
        # State tracking
        self._state['current_position_pct'] = 0.0
        self._state['mfi_values'] = None
    
    def initialize(self, df: pd.DataFrame) -> None:
        """
        Initialize strategy with market data.
        
        Calculates MFI values for the entire dataset.
        """
        self.validate_data(df)
        
        # CRITICAL: Ensure timezone-naive index before any calculations
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df = df.copy()
            df.index = df.index.tz_localize(None)
        
        # Calculate MFI for entire dataset
        try:
            mfi_values = self.mfi_indicator.calculate(df)
            
            # CRITICAL: Ensure MFI result has timezone-naive index
            if hasattr(mfi_values.index, 'tz') and mfi_values.index.tz is not None:
                mfi_values.index = mfi_values.index.tz_localize(None)
            
            self._state['mfi_values'] = mfi_values
            
            # Add MFI to dataframe for reference
            if 'MFI' not in df.columns:
                df['MFI'] = mfi_values
        except Exception as e:
            raise ValueError(f"Failed to calculate MFI: {e}")
    
    def get_momentum_value(self, df: pd.DataFrame, index: int) -> float:
        """Get MFI value at specific index."""
        if 'MFI' not in df.columns:
            self.initialize(df)
        return df['MFI'].iloc[index]
    
    def generate_signal(self, 
                       df: pd.DataFrame, 
                       index: int = -1) -> Optional[TradingSignal]:
        """
        Generate trading signal based on MFI levels.
        
        Args:
            df: DataFrame with OHLCV data
            index: Bar index (-1 for latest)
            
        Returns:
            TradingSignal or None
        """
        # Ensure MFI is calculated
        if 'MFI' not in df.columns:
            self.initialize(df)
        
        current_mfi = df['MFI'].iloc[index]
        current_price = df['Close'].iloc[index]
        
        # CRITICAL: Get timestamp and ensure it's completely timezone-naive
        if isinstance(df.index, pd.DatetimeIndex):
            current_time = df.index[index]
            
            # Strip timezone using .replace(tzinfo=None) which works for Timestamp objects
            if hasattr(current_time, 'tzinfo') and current_time.tzinfo is not None:
                current_time = current_time.replace(tzinfo=None)
            
            # Convert to plain Python datetime (removes all pandas metadata)
            current_time = current_time.to_pydatetime() if hasattr(current_time, 'to_pydatetime') else current_time
        else:
            current_time = datetime.now()
        
        # Skip if MFI is NaN (not enough data)
        if pd.isna(current_mfi):
            return None
        
        symbol = getattr(df, 'symbol', 'UNKNOWN')
        
        # === EXIT SIGNAL ===
        if current_mfi >= self.sell_threshold:
            return TradingSignal(
                timestamp=current_time,
                symbol=symbol,
                signal_type=SignalType.SELL,
                strength=SignalStrength.STRONG,
                price=Decimal(str(current_price)),
                strategy_name=self.name,
                reason=f"MFI overbought: {current_mfi:.1f} >= {self.sell_threshold}",
                recommended_position_size=Decimal('0'),  # Close all
                indicators={'MFI': current_mfi}
            )
        
        # === ENTRY SIGNALS ===
        # Check if we can still add to position
        current_position = self._state.get('current_position_pct', 0.0)
        
        if current_position < self.max_position_pct:
            # Strong buy signal (extreme oversold)
            if current_mfi <= self.strong_buy_threshold:
                return TradingSignal(
                    timestamp=current_time,
                    symbol=symbol,
                    signal_type=SignalType.STRONG_BUY,
                    strength=SignalStrength.VERY_STRONG,
                    price=Decimal(str(current_price)),
                    strategy_name=self.name,
                    reason=f"MFI extremely oversold: {current_mfi:.1f} <= {self.strong_buy_threshold}",
                    recommended_position_size=Decimal(str(self.strong_position_pct)),
                    indicators={'MFI': current_mfi}
                )
            
            # Normal buy signal (oversold)
            elif current_mfi <= self.buy_threshold:
                return TradingSignal(
                    timestamp=current_time,
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.STRONG,
                    price=Decimal(str(current_price)),
                    strategy_name=self.name,
                    reason=f"MFI oversold: {current_mfi:.1f} <= {self.buy_threshold}",
                    recommended_position_size=Decimal(str(self.normal_position_pct)),
                    indicators={'MFI': current_mfi}
                )
        
        # No signal
        return None
    
    def get_position_size(self, 
                         current_equity: float,
                         current_price: float,
                         signal: TradingSignal) -> float:
        """
        Calculate number of shares to trade.
        
        Args:
            current_equity: Current account value
            current_price: Current stock price
            signal: Trading signal with position size recommendation
            
        Returns:
            Number of shares (integer)
        """
        if signal.signal_type in [SignalType.SELL, SignalType.CLOSE]:
            # Return 0 to indicate "close all" - actual logic handled by backtesting engine
            return 0
        
        # Calculate position value
        position_value = current_equity * float(signal.recommended_position_size)
        
        # Calculate number of shares (Taiwan stocks trade in lots of 1000)
        shares = int(position_value / current_price)
        
        # Taiwan market: round to nearest 1000 shares (1 lot)
        # Comment this out if trading fractional shares or different market
        shares = (shares // 1000) * 1000
        
        return max(shares, 0)
    
    def update_position(self, position_pct: float) -> None:
        """
        Update internal position tracking.
        
        Args:
            position_pct: Current position size as percentage of equity
        """
        self._state['current_position_pct'] = position_pct
    
    def get_risk_metrics(self, df: pd.DataFrame) -> dict:
        """
        Calculate risk metrics for this strategy.
        
        Returns:
            Dict with risk metrics like max_position, avg_position, etc.
        """
        if 'MFI' not in df.columns:
            self.initialize(df)
        
        mfi_series = df['MFI'].dropna()
        
        buy_signals = (mfi_series <= self.buy_threshold).sum()
        strong_buy_signals = (mfi_series <= self.strong_buy_threshold).sum()
        sell_signals = (mfi_series >= self.sell_threshold).sum()
        
        return {
            'max_position_pct': self.max_position_pct,
            'buy_signals': buy_signals,
            'strong_buy_signals': strong_buy_signals,
            'sell_signals': sell_signals,
            'buy_ratio': buy_signals / len(mfi_series) if len(mfi_series) > 0 else 0,
            'sell_ratio': sell_signals / len(mfi_series) if len(mfi_series) > 0 else 0,
            'avg_mfi': mfi_series.mean(),
            'min_mfi': mfi_series.min(),
            'max_mfi': mfi_series.max(),
        }
    
    def optimize_params(self, df: pd.DataFrame) -> dict:
        """
        Suggest parameter ranges for optimization.
        
        Returns:
            Dict with parameter ranges for backtesting optimization
        """
        return {
            'mfi_period': range(10, 25, 2),  # 10, 12, 14, 16, 18, 20, 22, 24
            'buy_threshold': range(25, 45, 5),  # 25, 30, 35, 40
            'sell_threshold': range(75, 95, 5),  # 75, 80, 85, 90
            'strong_buy_threshold': range(15, 25, 5),  # 15, 20
        }
    
    def __repr__(self) -> str:
        return (f"MfiHunterStrategy(period={self.mfi_period}, "
                f"buy={self.buy_threshold}, sell={self.sell_threshold})")
