"""
Shioaji Data Provider Implementation.

Shioaji is the official Python API for Taiwan securities trading.
This will be the primary provider for live trading in Taiwan market.

Documentation: https://sinotrade.github.io/

NOTE: This is a template/skeleton. Implementation requires:
1. Shioaji package: pip install shioaji
2. API credentials from Sinopac Securities
3. Testing with actual account
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Callable
import pandas as pd
import time

from .base import TaiwanMarketProvider, RealtimeDataProvider


class ShioajiProvider(TaiwanMarketProvider, RealtimeDataProvider):
    """
    Shioaji implementation for Taiwan stock market.
    
    Features:
    - Real-time quotes
    - Historical data
    - Order execution (for live trading)
    - Market depth
    - Taiwan-specific features
    
    Requirements:
    - Sinopac Securities account
    - API key and secret
    """
    
    def __init__(self, api_key: str = None, secret_key: str = None, person_id: str = None):
        super().__init__("Shioaji")
        self.api_key = api_key
        self.secret_key = secret_key
        self.person_id = person_id
        self._api = None
        self._callbacks = {}
        self._subscriptions = []
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 0.5  # 500ms between requests
        self._request_count = 0
        self._request_window_start = 0
    
    def connect(self, **credentials) -> bool:
        """
        Connect to Shioaji API.
        
        Args:
            **credentials: Should include:
                - api_key: Your API key
                - secret_key: Your secret key
                - simulation: bool (default False) - use simulation environment
                
        Returns:
            True if connected successfully
        """
        try:
            # Import here to make it optional
            import shioaji as sj
            
            api_key = credentials.get('api_key', self.api_key)
            secret_key = credentials.get('secret_key', self.secret_key)
            person_id = credentials.get('person_id', self.person_id)
            simulation = credentials.get('simulation', True)  # Default to simulation for safety!
            
            if not all([api_key, secret_key]):
                raise ValueError("api_key and secret_key are required")
            
            # Initialize API
            self._api = sj.Shioaji(simulation=simulation)
            
            # Login (person_id not needed for current Shioaji version)
            print(f"🔌 Connecting to Shioaji ({'Simulation' if simulation else '⚠️  LIVE'} mode)...")
            accounts = self._api.login(
                api_key=api_key,
                secret_key=secret_key
            )
            
            if accounts:
                self._connected = True
                self._request_window_start = time.time()
                print(f"✅ Connected to Shioaji!")
                print(f"   Mode: {'Simulation (safe)' if simulation else '⚠️  LIVE TRADING'}")
                return True
            else:
                raise RuntimeError("Login failed")
                
        except ImportError:
            raise RuntimeError(
                "Shioaji not installed. Install with: pip install shioaji"
            )
        except Exception as e:
            print(f"Failed to connect to Shioaji: {e}")
            self._connected = False
            return False
    
    def _rate_limit_wait(self):
        """Enforce rate limits to avoid hitting API quota."""
        import time
        
        # Minimum interval between requests
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        
        self._last_request_time = time.time()
        self._request_count += 1
    
    def disconnect(self) -> None:
        """Logout and clean up."""
        if self._api:
            try:
                self._api.logout()
                print("👋 Disconnected from Shioaji")
            except:
                pass
            self._api = None
        
        self._callbacks.clear()
        self._subscriptions.clear()
        self._connected = False
    
    def get_historical_data(self,
                           symbol: str,
                           start_date: Optional[date] = None,
                           end_date: Optional[date] = None,
                           interval: str = '1d') -> pd.DataFrame:
        """
        Fetch historical data from Shioaji.
        
        Args:
            symbol: Taiwan stock code (e.g., '2337', '6944')
                   Will be converted to Shioaji contract format
            start_date: Start date
            end_date: End date  
            interval: Data interval
            
        Returns:
            DataFrame with OHLCV data
        """
        if not self._api:
            raise RuntimeError("Not connected. Call connect() first.")
        
        # Convert symbol to Shioaji contract
        contract = self._get_contract(symbol)
        
        # Default dates
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        try:
            # Rate limit protection
            self._rate_limit_wait()
            
            # Fetch kbars (candlestick data)
            print(f"📥 Fetching {symbol} from Shioaji ({start_date} to {end_date})...")
            kbars = self._api.kbars(
                contract=contract,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                timeout=30000  # 30 second timeout
            )
            
            # Convert to DataFrame
            if not kbars:
                print(f"⚠️  No data returned for {symbol}")
                return pd.DataFrame()
            
            df = pd.DataFrame({**kbars})
            
            # Rename columns to standard format
            df = df.rename(columns={
                'Open': 'Open',
                'High': 'High', 
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            })
            
            # Set datetime index
            if 'Time' in df.columns:
                df['Date'] = pd.to_datetime(df['Time'])
                df = df.set_index('Date')
            
            # Keep only OHLCV
            available_cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in df.columns]
            df = df[available_cols]
            
            # CRITICAL: Normalize timezone (strip Asia/Taipei)
            df = self._normalize_timezone(df)
            
            # Convert to numeric
            for col in available_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove NaN
            df = df.dropna()
            
            df.symbol = symbol
            
            print(f"✅ Fetched {len(df)} rows for {symbol}")
            
            return df
            
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data for {symbol}: {e}")
    
    def get_intraday_1min(self,
                          symbol: str,
                          target_date: date) -> pd.DataFrame:
        """
        Fetch 1-minute Kbars for a single trading day.
        Shioaji kbars returns 1-min when start==end (single day).
        
        Args:
            symbol: Stock code (e.g. '2330.TW')
            target_date: Date to fetch
            
        Returns:
            DataFrame with columns Open, High, Low, Close, Volume, datetime index
        """
        if not self._api:
            raise RuntimeError("Not connected. Call connect() first.")
        contract = self._get_contract(symbol)
        date_str = target_date.strftime('%Y-%m-%d')
        self._rate_limit_wait()
        kbars = self._api.kbars(
            contract=contract,
            start=date_str,
            end=date_str,
            timeout=30000,
        )
        if not kbars:
            return pd.DataFrame()
        df = pd.DataFrame({**kbars})
        ts_col = 'ts' if 'ts' in df.columns else 'Time'
        if ts_col not in df.columns:
            return pd.DataFrame()
        df['DateTime'] = pd.to_datetime(df[ts_col])
        df = df.set_index('DateTime')
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        df = self._normalize_timezone(df)
        df.symbol = symbol
        return df
    
    def _get_contract(self, symbol: str):
        """
        Get Shioaji contract object for a symbol.
        
        Args:
            symbol: Stock code (e.g., '2337' or '2337.TW')
            
        Returns:
            Shioaji Contract object
        """
        # Remove .TW suffix if present
        clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
        
        # Get contract from Shioaji
        try:
            contract = self._api.Contracts.Stocks[clean_symbol]
            return contract
        except KeyError:
            raise ValueError(f"Symbol {symbol} not found in Shioaji contracts")
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get real-time price quote.
        """
        if not self._api:
            raise RuntimeError("Not connected")
        
        contract = self._get_contract(symbol)
        
        try:
            quote = self._api.quote(contract)
            return quote.close  # Most recent price
        except Exception as e:
            print(f"Failed to get latest price for {symbol}: {e}")
            return None
    
    def get_multiple_symbols(self, 
                            symbols: List[str],
                            start_date: Optional[date] = None,
                            end_date: Optional[date] = None) -> dict[str, pd.DataFrame]:
        """
        Fetch data for multiple symbols.
        """
        result = {}
        
        for symbol in symbols:
            try:
                df = self.get_historical_data(symbol, start_date, end_date)
                result[symbol] = df
            except Exception as e:
                print(f"Warning: Failed to fetch {symbol}: {e}")
        
        return result
    
    def subscribe(self, symbols: List[str], callback: Callable) -> None:
        """
        Subscribe to real-time quotes.
        
        Args:
            symbols: List of stock codes
            callback: Function(symbol, quote_data)
        """
        if not self._api:
            raise RuntimeError("Not connected")
        
        for symbol in symbols:
            contract = self._get_contract(symbol)
            
            # Create wrapper callback
            def quote_callback(exchange, quote):
                callback(symbol, {
                    'price': quote.close,
                    'volume': quote.volume,
                    'timestamp': quote.datetime
                })
            
            # Subscribe
            self._api.quote.subscribe(
                contract,
                quote_type='tick',  # Tick-by-tick data
                version='v1'
            )
            
            self._callbacks[symbol] = quote_callback
            self._subscriptions.append(symbol)
    
    def unsubscribe(self, symbols: List[str]) -> None:
        """Unsubscribe from real-time quotes."""
        if not self._api:
            return
        
        for symbol in symbols:
            if symbol in self._subscriptions:
                contract = self._get_contract(symbol)
                self._api.quote.unsubscribe(contract)
                self._subscriptions.remove(symbol)
                
                if symbol in self._callbacks:
                    del self._callbacks[symbol]
    
    def get_market_status(self) -> dict:
        """Get Taiwan market status."""
        now = datetime.now()
        
        # Taiwan market hours: 9:00 - 13:30
        market_open = now.replace(hour=9, minute=0, second=0)
        market_close = now.replace(hour=13, minute=30, second=0)
        
        is_open = (
            self.is_trading_day(now.date()) and
            market_open <= now <= market_close
        )
        
        return {
            'is_open': is_open,
            'next_open': market_open if now < market_open else market_open + timedelta(days=1),
            'next_close': market_close if is_open else market_close + timedelta(days=1)
        }
    
    def search_symbol(self, query: str) -> List[dict]:
        """
        Search for Taiwan stocks.
        
        Shioaji provides access to all Taiwan stocks.
        """
        if not self._api:
            raise RuntimeError("Not connected")
        
        results = []
        query_lower = query.lower()
        
        # Search through all stock contracts
        for symbol, contract in self._api.Contracts.Stocks.items():
            if (query_lower in symbol.lower() or 
                query_lower in contract.name.lower()):
                results.append({
                    'symbol': symbol,
                    'name': contract.name,
                    'market': contract.exchange.value
                })
        
        return results[:20]  # Limit to 20 results
    
    @property
    def supported_intervals(self) -> List[str]:
        """Shioaji supported intervals."""
        return ['1m', '5m', '15m', '30m', '1h', '1d']
    
    def get_stock_info(self, symbol: str) -> dict:
        """Get detailed stock information."""
        if not self._api:
            raise RuntimeError("Not connected")
        
        contract = self._get_contract(symbol)
        
        return {
            'symbol': symbol,
            'name': contract.name,
            'exchange': contract.exchange.value,
            'category': contract.category,
            'unit': contract.unit,
            'limit_up': contract.limit_up,
            'limit_down': contract.limit_down,
            'reference': contract.reference,
        }
    
    def place_order(self, symbol: str, action: str, quantity: int, price: Optional[float] = None):
        """
        Place an order (for future live trading implementation).
        
        Args:
            symbol: Stock code
            action: 'Buy' or 'Sell'
            quantity: Number of shares
            price: Limit price (None for market order)
        """
        # TODO: Implement order placement
        # This is intentionally left as a stub for safety
        raise NotImplementedError(
            "Order placement not yet implemented. "
            "This requires careful testing and risk management."
        )
    
    def __repr__(self) -> str:
        status = "connected" if self._connected else "disconnected"
        subs = len(self._subscriptions)
        return f"ShioajiProvider(status={status}, subscriptions={subs})"
