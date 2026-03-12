"""
Data Service - Application layer service for data management.

This orchestrates data fetching, caching, and storage operations.
"""
from datetime import date, datetime, timedelta
from typing import Optional, List, Callable
import pandas as pd

from ...infrastructure.data_providers.base import DataProvider
from ...infrastructure.database.repository import MarketDataRepository


class DataService:
    """
    Service for managing market data.
    
    Responsibilities:
    - Fetch data from providers
    - Cache data in database
    - Serve data to strategies and UI
    - Handle data updates
    """
    
    def __init__(self, 
                 provider: DataProvider,
                 repository: MarketDataRepository,
                 fallback_provider: Optional[DataProvider] = None,
                 fallback_factory: Optional[Callable[[], Optional[DataProvider]]] = None):
        self.provider = provider
        self.repository = repository
        self._fallback_provider = fallback_provider
        self._fallback_factory = fallback_factory
        self._fallback_tried = fallback_provider is not None  # Skip factory if we already have one
    
    def get_data(self,
                 symbol: str,
                 start_date: Optional[date] = None,
                 end_date: Optional[date] = None,
                 use_cache: bool = True) -> pd.DataFrame:
        """
        Get market data with intelligent caching.
        
        Strategy:
        1. Check database cache first (if use_cache=True)
        2. If data is missing or stale, fetch from provider
        3. Update cache
        4. Return data
        
        Args:
            symbol: Stock symbol
            start_date: Start date (defaults to 1 year ago)
            end_date: End date (defaults to today)
            use_cache: Whether to use database cache
            
        Returns:
            DataFrame with OHLCV data
        """
        # Default dates
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        # Try cache first
        if use_cache:
            cached_data = self.repository.get_data(symbol, start_date, end_date)
            
            # Check if cache is complete and recent
            if not cached_data.empty:
                # Check if we need to update
                last_cached_date = cached_data.index[-1].date()
                
                # If cache is recent enough (within 1 day), use it
                if (end_date - last_cached_date).days <= 1:
                    return cached_data
                
                # Otherwise, fetch only new data (incremental update)
                new_start = last_cached_date + timedelta(days=1)
                if new_start <= end_date:
                    try:
                        new_data = self._fetch_from_provider(
                            symbol, new_start, end_date
                        )
                        if not new_data.empty:
                            # Save new data
                            self.repository.save_dataframe(new_data, symbol)
                            # Combine with cached data
                            combined = pd.concat([cached_data, new_data])
                            combined = combined[~combined.index.duplicated(keep='last')]
                            return combined
                    except Exception:
                        # yfinance 偶發失敗（台股、窄區間等）→ 直接用 cache
                        # 你的 daily import 已寫入 DB，不因 incremental 失敗而 crash
                        pass
                
                return cached_data
        
        # Cache miss or disabled - fetch from provider
        data = self._fetch_from_provider(symbol, start_date, end_date)
        
        if not data.empty and use_cache:
            # Update cache
            self.repository.save_dataframe(data, symbol)
        
        return data
    
    def _get_fallback_provider(self) -> Optional[DataProvider]:
        """Lazy-init fallback from factory (only when first needed)."""
        if self._fallback_provider is not None:
            return self._fallback_provider
        if self._fallback_factory and not self._fallback_tried:
            self._fallback_tried = True
            self._fallback_provider = self._fallback_factory()
        return self._fallback_provider

    def _fetch_from_provider(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Try primary provider, then fallback if configured."""
        last_error = None
        try:
            return self.provider.get_historical_data(symbol, start_date, end_date)
        except Exception as e:
            last_error = e
        fallback = self._get_fallback_provider()
        if fallback:
            try:
                return fallback.get_historical_data(
                    symbol, start_date, end_date
                )
            except Exception as e:
                last_error = e
        if last_error:
            raise last_error
        return pd.DataFrame()
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get the most recent price for a symbol."""
        return self.provider.get_latest_price(symbol)
    
    def get_multiple_symbols(self,
                            symbols: List[str],
                            start_date: Optional[date] = None,
                            end_date: Optional[date] = None,
                            use_cache: bool = True) -> dict[str, pd.DataFrame]:
        """
        Get data for multiple symbols.
        
        Returns:
            Dict mapping symbol to DataFrame
        """
        result = {}
        
        for symbol in symbols:
            try:
                df = self.get_data(symbol, start_date, end_date, use_cache)
                result[symbol] = df
            except Exception as e:
                print(f"Warning: Failed to fetch {symbol}: {e}")
        
        return result
    
    def refresh_symbol(self, 
                      symbol: str,
                      days_back: int = 365) -> int:
        """
        Force refresh data for a symbol.
        
        Args:
            symbol: Stock symbol
            days_back: Number of days to fetch
            
        Returns:
            Number of records updated
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        # Fetch fresh data
        data = self.provider.get_historical_data(symbol, start_date, end_date)
        
        if data.empty:
            return 0
        
        # Save to database
        return self.repository.save_dataframe(data, symbol)
    
    def get_available_symbols(self) -> List[str]:
        """Get list of symbols with cached data."""
        return self.repository.get_all_symbols()
    
    def get_data_info(self, symbol: str) -> dict:
        """
        Get information about available data for a symbol.
        
        Returns:
            Dict with statistics and metadata
        """
        stats = self.repository.get_statistics(symbol)
        
        # Try to get additional info from provider
        try:
            stock_info = self.provider.get_stock_info(symbol)
            stats.update(stock_info)
        except:
            pass
        
        return stats
    
    def search_stocks(self, query: str) -> List[dict]:
        """Search for stocks by symbol or name."""
        return self.provider.search_symbol(query)
    
    def ensure_data_available(self,
                             symbol: str,
                             required_days: int = 100) -> bool:
        """
        Ensure sufficient historical data is available.
        
        Args:
            symbol: Stock symbol
            required_days: Minimum number of days needed
            
        Returns:
            True if sufficient data is available
        """
        date_range = self.repository.get_date_range(symbol)
        
        if date_range is None:
            # No data - fetch it
            self.refresh_symbol(symbol, days_back=required_days + 50)
            date_range = self.repository.get_date_range(symbol)
        
        if date_range:
            days_available = (date_range[1] - date_range[0]).days
            return days_available >= required_days
        
        return False
