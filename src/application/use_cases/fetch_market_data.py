"""
Use Case: Fetch Market Data

Encapsulates the business logic for fetching and storing market data.
"""
from datetime import date, timedelta
from typing import Optional, List

from ..services.data_service import DataService


class FetchMarketDataUseCase:
    """
    Use case for fetching market data.
    
    This handles the complete workflow of:
    1. Validating symbol
    2. Fetching data from provider
    3. Storing in database
    4. Returning result
    """
    
    def __init__(self, data_service: DataService):
        self.data_service = data_service
    
    def execute(self,
                symbol: str,
                start_date: Optional[date] = None,
                end_date: Optional[date] = None,
                force_refresh: bool = False) -> dict:
        """
        Fetch market data for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., '2337.TW')
            start_date: Start date (defaults to 1 year ago)
            end_date: End date (defaults to today)
            force_refresh: Force re-download even if cached
            
        Returns:
            Dict with status and data info
        """
        # Validate inputs
        if not symbol or len(symbol) < 1:
            return {
                'success': False,
                'error': 'Invalid symbol'
            }
        
        # Set defaults
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        try:
            # Fetch data
            df = self.data_service.get_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                use_cache=not force_refresh
            )
            
            if df.empty:
                return {
                    'success': False,
                    'error': f'No data available for {symbol}'
                }
            
            # Get data info
            info = self.data_service.get_data_info(symbol)
            
            return {
                'success': True,
                'symbol': symbol,
                'rows': len(df),
                'start_date': df.index[0].strftime('%Y-%m-%d'),
                'end_date': df.index[-1].strftime('%Y-%m-%d'),
                'latest_close': float(df['Close'].iloc[-1]),
                'info': info
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_batch(self,
                     symbols: List[str],
                     start_date: Optional[date] = None,
                     end_date: Optional[date] = None) -> dict:
        """
        Fetch data for multiple symbols.
        
        Returns:
            Dict with results for each symbol
        """
        results = {}
        
        for symbol in symbols:
            results[symbol] = self.execute(symbol, start_date, end_date)
        
        # Summary
        successful = sum(1 for r in results.values() if r['success'])
        
        return {
            'total': len(symbols),
            'successful': successful,
            'failed': len(symbols) - successful,
            'results': results
        }
