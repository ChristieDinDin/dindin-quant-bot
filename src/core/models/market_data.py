"""
Core domain models for market data.
These models represent the business entities and should be framework-agnostic.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from decimal import Decimal


@dataclass
class OHLCV:
    """
    Open, High, Low, Close, Volume data model.
    Represents a single bar/candle of market data.
    """
    timestamp: datetime
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    
    def __post_init__(self):
        """Validate data integrity."""
        if self.high < self.low:
            raise ValueError(f"High ({self.high}) cannot be less than Low ({self.low})")
        if self.high < self.open or self.high < self.close:
            raise ValueError(f"High must be >= Open and Close")
        if self.low > self.open or self.low > self.close:
            raise ValueError(f"Low must be <= Open and Close")
        if self.volume < 0:
            raise ValueError(f"Volume cannot be negative")
    
    @property
    def typical_price(self) -> Decimal:
        """Calculate typical price (HLC/3)."""
        return (self.high + self.low + self.close) / Decimal('3')
    
    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish (close > open)."""
        return self.close > self.open
    
    @property
    def body_size(self) -> Decimal:
        """Get the size of the candle body."""
        return abs(self.close - self.open)
    
    @property
    def range_size(self) -> Decimal:
        """Get the total range (high - low)."""
        return self.high - self.low


@dataclass
class MarketDataFrame:
    """
    Collection of OHLCV bars for a specific symbol.
    Represents time-series market data.
    """
    symbol: str
    data: list[OHLCV] = field(default_factory=list)
    
    def __len__(self) -> int:
        return len(self.data)
    
    def add_bar(self, bar: OHLCV) -> None:
        """Add a new OHLCV bar to the collection."""
        if bar.symbol != self.symbol:
            raise ValueError(f"Bar symbol {bar.symbol} doesn't match {self.symbol}")
        self.data.append(bar)
    
    def get_latest(self, n: int = 1) -> list[OHLCV]:
        """Get the latest n bars."""
        return self.data[-n:] if n <= len(self.data) else self.data
    
    @property
    def latest_close(self) -> Optional[Decimal]:
        """Get the most recent close price."""
        return self.data[-1].close if self.data else None
    
    @property
    def date_range(self) -> tuple[datetime, datetime]:
        """Get the start and end dates."""
        if not self.data:
            raise ValueError("No data available")
        return self.data[0].timestamp, self.data[-1].timestamp
