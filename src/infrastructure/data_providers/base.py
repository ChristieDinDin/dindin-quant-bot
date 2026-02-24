"""
Abstract base class for market data providers.

This provides a unified interface for different data sources:
- yfinance (current)
- Shioaji (future)
- Taiwan bank APIs (future)
- Any other data source

Benefits:
- Easy to swap data providers
- Consistent interface across all providers
- Mock providers for testing
"""
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import Optional, List
import pandas as pd


class DataProvider(ABC):
    """
    Abstract interface for market data providers.
    
    All data providers must implement these methods to ensure
    compatibility with the rest of the system.
    """
    
    def __init__(self, name: str):
        self.name = name
        self._connected = False
    
    @abstractmethod
    def connect(self, **credentials) -> bool:
        """
        Establish connection to data source.
        
        Args:
            **credentials: Provider-specific credentials
            
        Returns:
            True if connected successfully
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to data source."""
        pass
    
    @abstractmethod
    def get_historical_data(self,
                           symbol: str,
                           start_date: Optional[date] = None,
                           end_date: Optional[date] = None,
                           interval: str = '1d') -> pd.DataFrame:
        """
        Fetch historical OHLCV data.
        
        Args:
            symbol: Stock symbol (e.g., '2337.TW')
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval ('1d', '1h', '5m', etc.)
            
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
            Index should be DatetimeIndex
        """
        pass
    
    @abstractmethod
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get the most recent price for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price or None if unavailable
        """
        pass
    
    @abstractmethod
    def get_multiple_symbols(self, 
                            symbols: List[str],
                            start_date: Optional[date] = None,
                            end_date: Optional[date] = None) -> dict[str, pd.DataFrame]:
        """
        Fetch data for multiple symbols efficiently.
        
        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date
            
        Returns:
            Dict mapping symbol to DataFrame
        """
        pass
    
    @abstractmethod
    def search_symbol(self, query: str) -> List[dict]:
        """
        Search for symbols by name or code.
        
        Args:
            query: Search query
            
        Returns:
            List of dicts with symbol info: {'symbol': '...', 'name': '...'}
        """
        pass
    
    @property
    def is_connected(self) -> bool:
        """Check if provider is connected."""
        return self._connected
    
    @property
    @abstractmethod
    def supported_intervals(self) -> List[str]:
        """List of supported data intervals."""
        pass
    
    @property
    @abstractmethod
    def supported_markets(self) -> List[str]:
        """List of supported markets (e.g., ['TW', 'US', 'HK'])."""
        pass
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if symbol is in correct format.
        Override for provider-specific validation.
        """
        return len(symbol) > 0
    
    def _normalize_timezone(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        CRITICAL: Normalize timezone to ensure compatibility with backtesting libraries.
        
        All data providers MUST return timezone-naive DatetimeIndex.
        This method should be called by all concrete providers in their data retrieval methods.
        
        Why: backtesting.py and other libraries are strict about timezone-naive data.
        yfinance returns Asia/Taipei for Taiwan stocks, Shioaji will too.
        
        Args:
            df: DataFrame with potentially timezone-aware index
            
        Returns:
            DataFrame with timezone-naive DatetimeIndex
        """
        if not isinstance(df, pd.DataFrame):
            return df
        
        # Normalize the index
        if isinstance(df.index, pd.DatetimeIndex):
            if df.index.tz is not None:
                # Strip timezone info
                df.index = df.index.tz_localize(None)
        elif hasattr(df.index, '__iter__'):
            # Handle case where index might be object dtype with Timestamp objects
            try:
                df.index = pd.DatetimeIndex(df.index)
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
            except (TypeError, ValueError):
                pass  # Keep original index if conversion fails
        
        # Also check datetime columns (if any)
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                if hasattr(df[col], 'dt') and hasattr(df[col].dt, 'tz'):
                    if df[col].dt.tz is not None:
                        df[col] = df[col].dt.tz_localize(None)
        
        return df
    
    def __enter__(self):
        """Context manager support."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.disconnect()
    
    def __repr__(self) -> str:
        status = "connected" if self._connected else "disconnected"
        return f"{self.__class__.__name__}(name='{self.name}', status='{status}')"


class RealtimeDataProvider(DataProvider):
    """
    Extended interface for providers that support real-time data.
    
    Use this for live trading with streaming data support.
    """
    
    @abstractmethod
    def subscribe(self, symbols: List[str], callback) -> None:
        """
        Subscribe to real-time updates for symbols.
        
        Args:
            symbols: List of symbols to watch
            callback: Function to call on each update
                     signature: callback(symbol, price, volume, timestamp)
        """
        pass
    
    @abstractmethod
    def unsubscribe(self, symbols: List[str]) -> None:
        """Stop receiving updates for symbols."""
        pass
    
    @abstractmethod
    def get_market_status(self) -> dict:
        """
        Get current market status.
        
        Returns:
            Dict with: {'is_open': bool, 'next_open': datetime, 'next_close': datetime}
        """
        pass


class TaiwanMarketProvider(DataProvider):
    """
    Base class for Taiwan-specific data providers.
    
    Adds Taiwan market specific functionality:
    - Market hours (9:00 - 13:30 TWM)
    - Trading day calendar
    - Circuit breaker info
    - Stock categories (listed, OTC, emerging)
    """
    
    def __init__(self, name: str):
        super().__init__(name)
        self._market_calendar = None
    
    @property
    def supported_markets(self) -> List[str]:
        return ['TW', 'TWO']  # Taiwan Stock Exchange, OTC
    
    def is_trading_day(self, check_date: date) -> bool:
        """
        Check if a date is a trading day in Taiwan.
        
        Args:
            check_date: Date to check
            
        Returns:
            True if it's a trading day
        """
        # Basic check: weekends
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # TODO: Add Taiwan public holidays
        # You can integrate with a holiday calendar library
        
        return True
    
    def get_market_hours(self) -> dict:
        """
        Get Taiwan stock market trading hours.
        
        Returns:
            Dict with market hours
        """
        return {
            'open': '09:00',
            'close': '13:30',
            'timezone': 'Asia/Taipei',
            'lunch_break': None,  # Taiwan doesn't have lunch break
        }
    
    @abstractmethod
    def get_stock_info(self, symbol: str) -> dict:
        """
        Get detailed stock information.
        
        Returns:
            Dict with: name, industry, market_cap, pe_ratio, etc.
        """
        pass
