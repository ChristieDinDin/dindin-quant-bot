"""
Money Flow Index (MFI) Indicator Implementation.

MFI is a momentum indicator that uses both price and volume to measure
buying and selling pressure. It's often called the volume-weighted RSI.

Formula:
1. Typical Price = (High + Low + Close) / 3
2. Raw Money Flow = Typical Price * Volume
3. Money Flow Ratio = (14-period Positive Money Flow) / (14-period Negative Money Flow)
4. MFI = 100 - (100 / (1 + Money Flow Ratio))

Range: 0-100
- MFI < 20: Extremely oversold (STRONG BUY opportunity)
- MFI < 30-35: Oversold (BUY signal)
- MFI > 80-85: Overbought (SELL signal)
- MFI > 95: Extremely overbought
"""
from typing import Optional
import pandas as pd
import numpy as np

from .base import MomentumIndicator


class MFI(MomentumIndicator):
    """
    Money Flow Index (MFI) implementation.
    
    Attributes:
        period: Lookback period for MFI calculation (default: 14)
        overbought: Level considered overbought (default: 80)
        oversold: Level considered oversold (default: 20)
        buy_threshold: Custom buy threshold (default: 35)
        sell_threshold: Custom sell threshold (default: 85)
    """
    
    def __init__(self, 
                 period: int = 14,
                 overbought: float = 80,
                 oversold: float = 20,
                 buy_threshold: float = 35,
                 sell_threshold: float = 85,
                 strong_buy_threshold: float = 20):
        super().__init__("MFI", period, overbought, oversold)
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.strong_buy_threshold = strong_buy_threshold
    
    def validate_params(self, **kwargs) -> bool:
        """Validate MFI parameters."""
        period = kwargs.get('period', self.period)
        
        if not isinstance(period, int) or period < 1:
            raise ValueError(f"Period must be a positive integer, got {period}")
        
        if period > 100:
            raise ValueError(f"Period {period} is unreasonably large (max: 100)")
        
        return True
    
    def calculate(self, df: pd.DataFrame, period: Optional[int] = None) -> pd.Series:
        """
        Calculate Money Flow Index.
        
        Args:
            df: DataFrame with columns: High, Low, Close, Volume
            period: Lookback period (overrides instance period if provided)
            
        Returns:
            pd.Series with MFI values
        """
        period = period or self.period
        self.validate_params(period=period)
        
        # Validate required columns
        required_cols = ['High', 'Low', 'Close', 'Volume']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # Data should already be timezone-naive from DataProvider
        df = df.copy()
        
        # 1. Calculate Typical Price
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        
        # 2. Calculate Raw Money Flow
        raw_money_flow = typical_price * df['Volume']
        
        # 3. Determine positive and negative money flow
        positive_flow = pd.Series(0.0, index=df.index, dtype='float64')
        negative_flow = pd.Series(0.0, index=df.index, dtype='float64')
        
        # Calculate price changes
        typical_price_diff = typical_price.diff()
        
        # Positive money flow (price increased)
        positive_flow[typical_price_diff > 0] = raw_money_flow[typical_price_diff > 0]
        
        # Negative money flow (price decreased)
        negative_flow[typical_price_diff < 0] = raw_money_flow[typical_price_diff < 0]
        
        # 4. Calculate Money Flow Ratio
        positive_mf_sum = positive_flow.rolling(window=period).sum()
        negative_mf_sum = negative_flow.rolling(window=period).sum()
        
        # Avoid division by zero
        money_flow_ratio = positive_mf_sum / negative_mf_sum.replace(0, np.nan)
        
        # 5. Calculate MFI
        mfi = 100 - (100 / (1 + money_flow_ratio))
        
        return mfi
    
    def get_signal(self, value: float, **thresholds) -> str:
        """
        Generate trading signal based on MFI value.
        
        Returns:
            'strong_buy', 'buy', 'sell', or 'hold'
        """
        buy_level = thresholds.get('buy_threshold', self.buy_threshold)
        sell_level = thresholds.get('sell_threshold', self.sell_threshold)
        strong_buy_level = thresholds.get('strong_buy_threshold', self.strong_buy_threshold)
        
        if value <= strong_buy_level:
            return 'strong_buy'
        elif value <= buy_level:
            return 'buy'
        elif value >= sell_level:
            return 'sell'
        else:
            return 'hold'
    
    def get_position_size_recommendation(self, value: float) -> float:
        """
        Recommend position size based on MFI value.
        
        Returns:
            Position size as decimal (0.0 to 1.0)
            - MFI < 20: 0.30 (30% - strong buy)
            - MFI < buy_threshold: 0.15 (15% - normal buy)
            - Otherwise: 0.0 (no position)
        """
        if value <= self.strong_buy_threshold:
            return 0.30  # 30% position for extreme oversold
        elif value <= self.buy_threshold:
            return 0.15  # 15% position for normal oversold
        else:
            return 0.0  # No new position
    
    def calculate_with_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MFI and add signal metadata.
        
        Returns:
            DataFrame with additional columns: MFI, MFI_Signal, MFI_PositionSize
        """
        result = df.copy()
        result['MFI'] = self.calculate(df)
        result['MFI_Signal'] = result['MFI'].apply(self.get_signal)
        result['MFI_PositionSize'] = result['MFI'].apply(self.get_position_size_recommendation)
        
        return result
    
    def get_divergence(self, df: pd.DataFrame, price_col: str = 'Close') -> pd.Series:
        """
        Detect bullish/bearish divergence between price and MFI.
        
        Bullish divergence: Price makes lower low, but MFI makes higher low
        Bearish divergence: Price makes higher high, but MFI makes lower high
        
        Returns:
            pd.Series with values: 'bullish', 'bearish', or None
        """
        mfi = self.calculate(df)
        
        # This is a simplified version - you can enhance with peak detection
        divergence = pd.Series(None, index=df.index)
        
        # TODO: Implement sophisticated divergence detection
        # For now, this is a placeholder
        
        return divergence
    
    def __repr__(self) -> str:
        return (f"MFI(period={self.period}, "
                f"buy={self.buy_threshold}, "
                f"sell={self.sell_threshold})")
