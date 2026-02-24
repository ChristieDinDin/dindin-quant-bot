"""
Data repository for market data operations.

Provides high-level interface for data storage and retrieval.
This layer abstracts the database operations from the rest of the system.
"""
from datetime import datetime, date
from typing import Optional, List
import pandas as pd

from .connection import DatabaseConnection
from ..data_providers.base import DataProvider


class MarketDataRepository:
    """
    Repository for market data CRUD operations.
    
    This provides a clean interface for:
    - Storing historical data
    - Querying data by symbol and date range
    - Checking data availability
    - Managing data updates
    """
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
        self._ensure_schema()
    
    def _ensure_schema(self) -> None:
        """Ensure the database schema exists."""
        if not self.db.table_exists('daily_kline'):
            self._create_schema()
    
    def _create_schema(self) -> None:
        """Create the database schema."""
        with self.db.transaction() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_kline (
                    date TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (date, symbol)
                )
            ''')
            
            # Create indexes for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_symbol_date 
                ON daily_kline(symbol, date)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_date 
                ON daily_kline(date)
            ''')
    
    def save_dataframe(self, df: pd.DataFrame, symbol: str) -> int:
        """
        Save a DataFrame of OHLCV data.
        
        Args:
            df: DataFrame with columns: Open, High, Low, Close, Volume
                Index should be DatetimeIndex
            symbol: Stock symbol
            
        Returns:
            Number of rows inserted/updated
        """
        if df.empty:
            return 0
        
        # Prepare data for insertion
        df_copy = df.copy()
        df_copy['symbol'] = symbol
        df_copy['date'] = df_copy.index.strftime('%Y-%m-%d')
        
        # Select and order columns
        columns = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        df_copy.columns = [c.lower() for c in df_copy.columns]
        
        records = []
        for _, row in df_copy.iterrows():
            records.append((
                row['date'],
                row['symbol'],
                float(row['open']),
                float(row['high']),
                float(row['low']),
                float(row['close']),
                int(row['volume'])
            ))
        
        # Insert or replace (upsert)
        query = '''
            INSERT OR REPLACE INTO daily_kline 
            (date, symbol, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        
        self.db.executemany(query, records)
        
        return len(records)
    
    def get_data(self, 
                 symbol: str,
                 start_date: Optional[date] = None,
                 end_date: Optional[date] = None) -> pd.DataFrame:
        """
        Retrieve OHLCV data for a symbol.
        
        Args:
            symbol: Stock symbol
            start_date: Start date (optional)
            end_date: End date (optional)
            
        Returns:
            DataFrame with OHLCV data
        """
        query = '''
            SELECT date, open, high, low, close, volume
            FROM daily_kline
            WHERE symbol = ?
        '''
        params = [symbol]
        
        if start_date:
            query += ' AND date >= ?'
            params.append(start_date.strftime('%Y-%m-%d'))
        
        if end_date:
            query += ' AND date <= ?'
            params.append(end_date.strftime('%Y-%m-%d'))
        
        query += ' ORDER BY date ASC'
        
        results = self.db.fetchall(query, tuple(params))
        
        if not results:
            return pd.DataFrame()
        
        # Convert to DataFrame with properly capitalized columns
        df = pd.DataFrame({
            'Date': pd.to_datetime([row['date'] for row in results]),
            'Open': [float(row['open']) for row in results],
            'High': [float(row['high']) for row in results],
            'Low': [float(row['low']) for row in results],
            'Close': [float(row['close']) for row in results],
            'Volume': [int(row['volume']) for row in results],
        })
        
        # Set date as index
        df = df.set_index('Date')
        
        # Sort by date
        df = df.sort_index()
        
        # Add symbol as attribute (not column)
        df.symbol = symbol
        
        return df
    
    def has_data(self, symbol: str, check_date: Optional[date] = None) -> bool:
        """
        Check if data exists for a symbol (and optionally specific date).
        
        Args:
            symbol: Stock symbol
            check_date: Specific date to check (optional)
            
        Returns:
            True if data exists
        """
        if check_date:
            query = '''
                SELECT COUNT(*) as count FROM daily_kline
                WHERE symbol = ? AND date = ?
            '''
            params = (symbol, check_date.strftime('%Y-%m-%d'))
        else:
            query = '''
                SELECT COUNT(*) as count FROM daily_kline
                WHERE symbol = ?
            '''
            params = (symbol,)
        
        result = self.db.fetchone(query, params)
        return result['count'] > 0
    
    def get_date_range(self, symbol: str) -> Optional[tuple[date, date]]:
        """
        Get the date range of available data for a symbol.
        
        Returns:
            Tuple of (start_date, end_date) or None if no data
        """
        query = '''
            SELECT MIN(date) as min_date, MAX(date) as max_date
            FROM daily_kline
            WHERE symbol = ?
        '''
        
        result = self.db.fetchone(query, (symbol,))
        
        if result and result['min_date'] and result['max_date']:
            min_date = datetime.strptime(result['min_date'], '%Y-%m-%d').date()
            max_date = datetime.strptime(result['max_date'], '%Y-%m-%d').date()
            return (min_date, max_date)
        
        return None
    
    def get_all_symbols(self) -> List[str]:
        """Get list of all symbols in database."""
        query = '''
            SELECT DISTINCT symbol FROM daily_kline
            ORDER BY symbol
        '''
        
        results = self.db.fetchall(query)
        return [row['symbol'] for row in results]
    
    def delete_symbol(self, symbol: str) -> int:
        """
        Delete all data for a symbol.
        
        Returns:
            Number of rows deleted
        """
        with self.db.transaction() as cursor:
            cursor.execute('''
                DELETE FROM daily_kline WHERE symbol = ?
            ''', (symbol,))
            return cursor.rowcount
    
    def delete_date_range(self, symbol: str, 
                         start_date: date, 
                         end_date: date) -> int:
        """
        Delete data for a symbol within a date range.
        
        Returns:
            Number of rows deleted
        """
        with self.db.transaction() as cursor:
            cursor.execute('''
                DELETE FROM daily_kline 
                WHERE symbol = ? AND date >= ? AND date <= ?
            ''', (symbol, start_date.strftime('%Y-%m-%d'), 
                  end_date.strftime('%Y-%m-%d')))
            return cursor.rowcount
    
    def get_statistics(self, symbol: str) -> dict:
        """
        Get statistics about stored data for a symbol.
        
        Returns:
            Dict with count, date_range, latest_price, etc.
        """
        query = '''
            SELECT 
                COUNT(*) as count,
                MIN(date) as first_date,
                MAX(date) as last_date,
                AVG(volume) as avg_volume
            FROM daily_kline
            WHERE symbol = ?
        '''
        
        result = self.db.fetchone(query, (symbol,))
        
        if not result or result['count'] == 0:
            return {'count': 0}
        
        # Get latest price
        latest_query = '''
            SELECT close FROM daily_kline
            WHERE symbol = ? AND date = ?
        '''
        latest = self.db.fetchone(latest_query, (symbol, result['last_date']))
        
        return {
            'symbol': symbol,
            'count': result['count'],
            'first_date': result['first_date'],
            'last_date': result['last_date'],
            'latest_close': latest['close'] if latest else None,
            'avg_volume': result['avg_volume']
        }
    
    def sync_from_provider(self, 
                          symbol: str,
                          provider: DataProvider,
                          start_date: Optional[date] = None,
                          end_date: Optional[date] = None,
                          force_update: bool = False) -> int:
        """
        Sync data from a data provider to database.
        
        Args:
            symbol: Stock symbol
            provider: DataProvider instance
            start_date: Start date (optional)
            end_date: End date (optional)
            force_update: If True, re-download all data
            
        Returns:
            Number of new records added
        """
        # Check existing data range
        if not force_update:
            date_range = self.get_date_range(symbol)
            if date_range:
                # Only fetch data after the latest date
                start_date = date_range[1]
        
        # Fetch data from provider
        df = provider.get_historical_data(symbol, start_date, end_date)
        
        if df.empty:
            return 0
        
        # Save to database
        return self.save_dataframe(df, symbol)
