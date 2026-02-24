"""
yfinance Data Provider Implementation.

Current data source for the project.
Will be gradually replaced/supplemented with Shioaji and Taiwan bank APIs.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List
import pandas as pd
import yfinance as yf

from .base import TaiwanMarketProvider


class YFinanceProvider(TaiwanMarketProvider):
    """
    yfinance implementation of DataProvider.
    
    Good for:
    - Historical data
    - Free access
    - Multiple markets
    
    Limitations:
    - Not real-time
    - Rate limits
    - May have data gaps
    """
    
    def __init__(self):
        super().__init__("yfinance")
        self._tickers = {}  # Cache ticker objects
    
    def connect(self, **credentials) -> bool:
        """
        yfinance doesn't require authentication.
        """
        self._connected = True
        return True
    
    def disconnect(self) -> None:
        """Clear cached tickers."""
        self._tickers.clear()
        self._connected = False
    
    def _get_ticker(self, symbol: str) -> yf.Ticker:
        """Get or create cached ticker object."""
        if symbol not in self._tickers:
            self._tickers[symbol] = yf.Ticker(symbol)
        return self._tickers[symbol]
    
    def get_historical_data(self,
                           symbol: str,
                           start_date: Optional[date] = None,
                           end_date: Optional[date] = None,
                           interval: str = '1d') -> pd.DataFrame:
        """
        Fetch historical OHLCV data from yfinance.
        
        Args:
            symbol: Stock symbol (e.g., '2337.TW', '6944.TW')
            start_date: Start date (defaults to 1 year ago)
            end_date: End date (defaults to today)
            interval: '1d', '1wk', '1mo', '1h', '5m', etc.
            
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        # Default date range: 1 year
        if start_date is None:
            start_date = date.today() - timedelta(days=365)
        if end_date is None:
            end_date = date.today()
        
        ticker = self._get_ticker(symbol)
        
        try:
            # Download data
            df = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
                auto_adjust=False  # Keep original OHLC
            )
            
            if df.empty:
                raise ValueError(f"No data returned for {symbol}")
            
            # Clean up the dataframe
            df = self._clean_dataframe(df, symbol)
            
            return df
            
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data for {symbol}: {e}")
    
    def _clean_dataframe(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Clean and standardize the dataframe.
        
        - Handle multi-level columns from yfinance
        - Ensure consistent column names
        - Remove NaN values
        - CRITICAL: Normalize timezone (yfinance returns Asia/Taipei for Taiwan stocks)
        - Add symbol metadata
        """
        # If multi-level columns, flatten them
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        # Standardize column names (capitalize first letter)
        df.columns = [col.capitalize() for col in df.columns]
        
        # Keep only OHLCV columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols].copy()  # Use .copy() to avoid SettingWithCopyWarning
        
        # Convert to numeric and handle errors
        for col in available_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove rows with NaN values
        df = df.dropna()
        
        # CRITICAL: Normalize timezone at the source
        # This ensures all downstream code (indicators, strategies, backtesting) 
        # never has to deal with timezone issues
        df = self._normalize_timezone(df)
        
        # Add symbol as attribute (not column, to save memory)
        df.symbol = symbol
        
        return df
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get the most recent price.
        
        Note: yfinance doesn't provide true real-time data.
        This returns the last close price.
        """
        try:
            ticker = self._get_ticker(symbol)
            info = ticker.fast_info
            return info.last_price
        except Exception as e:
            print(f"Warning: Could not fetch latest price for {symbol}: {e}")
            return None
    
    def get_multiple_symbols(self, 
                            symbols: List[str],
                            start_date: Optional[date] = None,
                            end_date: Optional[date] = None) -> dict[str, pd.DataFrame]:
        """
        Fetch data for multiple symbols.
        
        yfinance supports batch downloads which is more efficient.
        """
        if start_date is None:
            start_date = date.today() - timedelta(days=365)
        if end_date is None:
            end_date = date.today()
        
        try:
            # Batch download
            data = yf.download(
                symbols,
                start=start_date,
                end=end_date,
                group_by='ticker',
                auto_adjust=False,
                progress=False
            )
            
            result = {}
            
            # Handle single vs multiple symbols
            if len(symbols) == 1:
                symbol = symbols[0]
                result[symbol] = self._clean_dataframe(data, symbol)
            else:
                # Multi-symbol returns different structure
                for symbol in symbols:
                    if symbol in data.columns.levels[0]:
                        df = data[symbol]
                        result[symbol] = self._clean_dataframe(df, symbol)
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"Failed to fetch multiple symbols: {e}")
    
    def search_symbol(self, query: str) -> List[dict]:
        """
        Search for Taiwan stocks by code or name.
        
        Note: yfinance doesn't have a native search API.
        This is a basic implementation.
        """
        # This is a placeholder - yfinance doesn't support search
        # You'll need a separate Taiwan stock list database
        results = []
        
        # Try as exact symbol
        try:
            symbol = query if '.TW' in query else f"{query}.TW"
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if info.get('symbol'):
                results.append({
                    'symbol': symbol,
                    'name': info.get('longName', info.get('shortName', 'Unknown')),
                    'market': 'TW'
                })
        except:
            pass
        
        return results
    
    @property
    def supported_intervals(self) -> List[str]:
        """yfinance supported intervals."""
        return ['1m', '2m', '5m', '15m', '30m', '60m', '90m', 
                '1h', '1d', '5d', '1wk', '1mo', '3mo']
    
    def get_stock_info(self, symbol: str) -> dict:
        """
        Get detailed stock information from yfinance.
        """
        ticker = self._get_ticker(symbol)
        try:
            info = ticker.info
            return {
                'symbol': symbol,
                'name': info.get('longName', info.get('shortName', 'Unknown')),
                'industry': info.get('industry', 'Unknown'),
                'sector': info.get('sector', 'Unknown'),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
            }
        except Exception as e:
            return {'symbol': symbol, 'error': str(e)}
    
    def __repr__(self) -> str:
        return f"YFinanceProvider(cached_tickers={len(self._tickers)})"
