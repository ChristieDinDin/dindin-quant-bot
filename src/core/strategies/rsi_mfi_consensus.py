"""
RSI + MFI Consensus Strategy.

This strategy uses both RSI and MFI indicators for confirmation.
Only trades when both indicators agree, increasing signal reliability.

Strategy Logic:
- BUY: Both RSI < 30 AND MFI < 35 (double oversold confirmation)
- STRONG BUY: Both RSI < 20 AND MFI < 20 (extreme oversold)
- SELL: Both RSI > 70 AND MFI > 85 (double overbought confirmation)

Benefits:
- Higher win rate (requires consensus)
- Fewer false signals
- More confident entries/exits

Drawbacks:
- Fewer trades (misses some opportunities)
- May miss early entries (waiting for confirmation)
"""
from typing import Optional
from datetime import datetime
from decimal import Decimal
import pandas as pd

from .base import MomentumStrategy
from ..models.signal import TradingSignal, SignalType, SignalStrength
from ..indicators.rsi import RSI
from ..indicators.mfi import MFI


class RsiMfiConsensusStrategy(MomentumStrategy):
    """
    Dual momentum confirmation strategy using RSI and MFI.
    
    Features:
    - Requires both indicators to agree before trading
    - Tiered position sizing based on signal strength
    - Risk management with max position limits
    """
    
    def __init__(self,
                 rsi_period: int = 14,
                 mfi_period: int = 14,
                 rsi_oversold: float = 30,
                 rsi_overbought: float = 70,
                 mfi_oversold: float = 35,
                 mfi_overbought: float = 85,
                 strong_threshold: float = 20,
                 max_position_pct: float = 0.80,
                 normal_position_pct: float = 0.15,
                 strong_position_pct: float = 0.30):
        """
        Initialize RSI + MFI Consensus strategy.
        
        Args:
            rsi_period: RSI calculation period (default: 14)
            mfi_period: MFI calculation period (default: 14)
            rsi_oversold: RSI oversold threshold (default: 30)
            rsi_overbought: RSI overbought threshold (default: 70)
            mfi_oversold: MFI oversold threshold (default: 35)
            mfi_overbought: MFI overbought threshold (default: 85)
            strong_threshold: Threshold for strong buy signals (default: 20)
            max_position_pct: Maximum total position size (default: 0.80)
            normal_position_pct: Position size for normal signals (default: 0.15)
            strong_position_pct: Position size for strong signals (default: 0.30)
        """
        super().__init__(
            name="RSI + MFI Consensus",
            description="Dual momentum confirmation using RSI and MFI indicators"
        )
        
        # Strategy parameters
        self.rsi_period = rsi_period
        self.mfi_period = mfi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.mfi_oversold = mfi_oversold
        self.mfi_overbought = mfi_overbought
        self.strong_threshold = strong_threshold
        self.max_position_pct = max_position_pct
        self.normal_position_pct = normal_position_pct
        self.strong_position_pct = strong_position_pct
        
        # Initialize indicators
        self.rsi_indicator = RSI(
            period=rsi_period,
            overbought=rsi_overbought,
            oversold=rsi_oversold
        )
        self.mfi_indicator = MFI(
            period=mfi_period,
            buy_threshold=mfi_oversold,
            sell_threshold=mfi_overbought
        )
        
        self.add_indicator('RSI', self.rsi_indicator)
        self.add_indicator('MFI', self.mfi_indicator)
        
        # State tracking
        self._state['current_position_pct'] = 0.0
        self._state['rsi_values'] = None
        self._state['mfi_values'] = None
    
    def initialize(self, df: pd.DataFrame) -> None:
        """
        Initialize strategy with market data.
        
        Calculates both RSI and MFI values for the entire dataset.
        """
        self.validate_data(df)
        
        # Calculate indicators
        try:
            self._state['rsi_values'] = self.rsi_indicator.calculate(df)
            self._state['mfi_values'] = self.mfi_indicator.calculate(df)
            
            # Add to dataframe
            if 'RSI' not in df.columns:
                df['RSI'] = self._state['rsi_values']
            if 'MFI' not in df.columns:
                df['MFI'] = self._state['mfi_values']
                
        except Exception as e:
            raise ValueError(f"Failed to initialize indicators: {e}")
    
    def generate_signal(self, 
                       df: pd.DataFrame, 
                       index: int = -1) -> Optional[TradingSignal]:
        """
        Generate trading signal based on RSI + MFI consensus.
        
        Args:
            df: DataFrame with OHLCV data
            index: Bar index (-1 for latest)
            
        Returns:
            TradingSignal or None
        """
        # Ensure indicators are calculated
        if 'RSI' not in df.columns or 'MFI' not in df.columns:
            self.initialize(df)
        
        current_rsi = df['RSI'].iloc[index]
        current_mfi = df['MFI'].iloc[index]
        current_price = df['Close'].iloc[index]
        
        # CRITICAL: Get timestamp and ensure it's timezone-naive
        if isinstance(df.index, pd.DatetimeIndex):
            current_time = df.index[index]
            # Strip timezone if present
            if hasattr(current_time, 'tz') and current_time.tz is not None:
                current_time = current_time.tz_localize(None)
            # Convert Timestamp to datetime
            current_time = current_time.to_pydatetime() if hasattr(current_time, 'to_pydatetime') else current_time
        else:
            current_time = datetime.now()
        
        # Skip if either indicator is NaN
        if pd.isna(current_rsi) or pd.isna(current_mfi):
            return None
        
        symbol = getattr(df, 'symbol', 'UNKNOWN')
        
        # === EXIT SIGNAL (Both indicators overbought) ===
        if current_rsi >= self.rsi_overbought and current_mfi >= self.mfi_overbought:
            return TradingSignal(
                timestamp=current_time,
                symbol=symbol,
                signal_type=SignalType.SELL,
                strength=SignalStrength.STRONG,
                price=Decimal(str(current_price)),
                strategy_name=self.name,
                reason=f"Consensus SELL: RSI={current_rsi:.1f}, MFI={current_mfi:.1f} (both overbought)",
                recommended_position_size=Decimal('0'),
                indicators={'RSI': current_rsi, 'MFI': current_mfi}
            )
        
        # === ENTRY SIGNALS (Both indicators oversold) ===
        current_position = self._state.get('current_position_pct', 0.0)
        
        if current_position < self.max_position_pct:
            # Check for consensus
            rsi_oversold = current_rsi <= self.rsi_oversold
            mfi_oversold = current_mfi <= self.mfi_oversold
            
            # STRONG BUY: Both extremely oversold
            if current_rsi <= self.strong_threshold and current_mfi <= self.strong_threshold:
                return TradingSignal(
                    timestamp=current_time,
                    symbol=symbol,
                    signal_type=SignalType.STRONG_BUY,
                    strength=SignalStrength.VERY_STRONG,
                    price=Decimal(str(current_price)),
                    strategy_name=self.name,
                    reason=f"Consensus STRONG BUY: RSI={current_rsi:.1f}, MFI={current_mfi:.1f} (both extreme oversold)",
                    recommended_position_size=Decimal(str(self.strong_position_pct)),
                    indicators={'RSI': current_rsi, 'MFI': current_mfi}
                )
            
            # NORMAL BUY: Both oversold (but not extreme)
            elif rsi_oversold and mfi_oversold:
                return TradingSignal(
                    timestamp=current_time,
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.STRONG,
                    price=Decimal(str(current_price)),
                    strategy_name=self.name,
                    reason=f"Consensus BUY: RSI={current_rsi:.1f}, MFI={current_mfi:.1f} (both oversold)",
                    recommended_position_size=Decimal(str(self.normal_position_pct)),
                    indicators={'RSI': current_rsi, 'MFI': current_mfi}
                )
        
        # No consensus signal
        return None
    
    def get_momentum_value(self, df: pd.DataFrame, index: int) -> float:
        """Get average momentum from both indicators."""
        if 'RSI' not in df.columns or 'MFI' not in df.columns:
            self.initialize(df)
        
        rsi = df['RSI'].iloc[index]
        mfi = df['MFI'].iloc[index]
        
        # Return average of both
        return (rsi + mfi) / 2
    
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
            return 0
        
        # Calculate position value
        position_value = current_equity * float(signal.recommended_position_size)
        
        # Calculate number of shares
        shares = int(position_value / current_price)
        
        # Taiwan market: round to nearest 1000 shares (1 lot)
        shares = (shares // 1000) * 1000
        
        return max(shares, 0)
    
    def update_position(self, position_pct: float) -> None:
        """Update internal position tracking."""
        self._state['current_position_pct'] = position_pct
    
    def get_indicator_agreement(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate how often RSI and MFI agree.
        
        Returns:
            Series showing agreement level (-1 to 1)
        """
        if 'RSI' not in df.columns or 'MFI' not in df.columns:
            self.initialize(df)
        
        # Normalize both to -1 to 1 scale
        rsi_norm = (df['RSI'] - 50) / 50
        mfi_norm = (df['MFI'] - 50) / 50
        
        # Agreement = sign(RSI) == sign(MFI)
        agreement = (rsi_norm * mfi_norm).apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)
        
        return agreement
    
    def get_risk_metrics(self, df: pd.DataFrame) -> dict:
        """Calculate risk metrics for this strategy."""
        if 'RSI' not in df.columns or 'MFI' not in df.columns:
            self.initialize(df)
        
        rsi_series = df['RSI'].dropna()
        mfi_series = df['MFI'].dropna()
        
        # Count consensus signals
        both_oversold = ((rsi_series <= self.rsi_oversold) & 
                        (mfi_series <= self.mfi_oversold)).sum()
        both_overbought = ((rsi_series >= self.rsi_overbought) & 
                          (mfi_series >= self.mfi_overbought)).sum()
        
        # Count strong signals
        both_extreme_oversold = ((rsi_series <= self.strong_threshold) & 
                                (mfi_series <= self.strong_threshold)).sum()
        
        return {
            'max_position_pct': self.max_position_pct,
            'consensus_buy_signals': both_oversold,
            'consensus_sell_signals': both_overbought,
            'strong_buy_signals': both_extreme_oversold,
            'signal_ratio': both_oversold / len(rsi_series) if len(rsi_series) > 0 else 0,
            'avg_rsi': rsi_series.mean(),
            'avg_mfi': mfi_series.mean(),
        }
    
    def __repr__(self) -> str:
        return (f"RsiMfiConsensusStrategy(RSI={self.rsi_period}, MFI={self.mfi_period}, "
                f"RSI_oversold={self.rsi_oversold}, MFI_oversold={self.mfi_oversold})")
