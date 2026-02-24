"""
Helper utilities and common functions.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List
import pandas as pd


def format_currency(amount: float, currency: str = "TWD") -> str:
    """
    Format currency amount.
    
    Args:
        amount: Amount to format
        currency: Currency code (default: TWD)
        
    Returns:
        Formatted string
    """
    if currency == "TWD":
        return f"NT$ {amount:,.0f}"
    else:
        return f"{currency} {amount:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format percentage value.
    
    Args:
        value: Percentage value (e.g., 15.5 for 15.5%)
        decimals: Number of decimal places
        
    Returns:
        Formatted string
    """
    return f"{value:.{decimals}f}%"


def calculate_returns(prices: pd.Series) -> pd.Series:
    """
    Calculate percentage returns from price series.
    
    Args:
        prices: Series of prices
        
    Returns:
        Series of percentage returns
    """
    return prices.pct_change() * 100


def calculate_sharpe_ratio(returns: pd.Series, 
                          risk_free_rate: float = 0.0,
                          periods_per_year: int = 252) -> float:
    """
    Calculate Sharpe ratio.
    
    Args:
        returns: Series of returns (as decimals, not percentages)
        risk_free_rate: Annual risk-free rate (default: 0)
        periods_per_year: Number of periods in a year (default: 252 trading days)
        
    Returns:
        Sharpe ratio
    """
    excess_returns = returns - (risk_free_rate / periods_per_year)
    return (excess_returns.mean() / excess_returns.std()) * (periods_per_year ** 0.5)


def get_trading_days(start_date: date, 
                    end_date: date,
                    exclude_weekends: bool = True) -> List[date]:
    """
    Get list of trading days between two dates.
    
    Args:
        start_date: Start date
        end_date: End date
        exclude_weekends: Whether to exclude weekends
        
    Returns:
        List of dates
    """
    days = []
    current = start_date
    
    while current <= end_date:
        if not exclude_weekends or current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    
    return days


def is_market_open(check_time: Optional[datetime] = None,
                  timezone: str = 'Asia/Taipei') -> bool:
    """
    Check if Taiwan stock market is open.
    
    Args:
        check_time: Time to check (defaults to now)
        timezone: Timezone (default: Asia/Taipei)
        
    Returns:
        True if market is open
    """
    if check_time is None:
        check_time = datetime.now()
    
    # Check if weekday
    if check_time.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Check market hours (9:00 - 13:30 Taiwan time)
    market_open = check_time.replace(hour=9, minute=0, second=0)
    market_close = check_time.replace(hour=13, minute=30, second=0)
    
    return market_open <= check_time <= market_close


def validate_symbol(symbol: str, market: str = 'TW') -> bool:
    """
    Validate stock symbol format.
    
    Args:
        symbol: Symbol to validate
        market: Market code (TW, US, etc.)
        
    Returns:
        True if valid
    """
    if market == 'TW':
        # Taiwan stocks: 4 digits + .TW or .TWO
        if '.TW' in symbol or '.TWO' in symbol:
            code = symbol.split('.')[0]
            return code.isdigit() and len(code) == 4
        # Just the number
        return symbol.isdigit() and len(symbol) == 4
    
    return len(symbol) > 0


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize OHLCV dataframe.
    
    Args:
        df: Input dataframe
        
    Returns:
        Cleaned dataframe
    """
    df = df.copy()
    
    # Standardize column names
    df.columns = [col.capitalize() for col in df.columns]
    
    # Remove rows with NaN
    df = df.dropna()
    
    # Ensure numeric types
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Remove any rows that became NaN after conversion
    df = df.dropna()
    
    # Sort by date
    df = df.sort_index()
    
    return df


def calculate_position_size(equity: float,
                           price: float,
                           position_pct: float,
                           lot_size: int = 1) -> int:
    """
    Calculate position size in shares.
    
    Args:
        equity: Current account equity
        price: Stock price
        position_pct: Position size as percentage (0.0 to 1.0)
        lot_size: Minimum lot size (default: 1 for most markets, 1000 for Taiwan)
        
    Returns:
        Number of shares to buy
    """
    position_value = equity * position_pct
    shares = int(position_value / price)
    
    # Round down to nearest lot
    if lot_size > 1:
        shares = (shares // lot_size) * lot_size
    
    return max(shares, 0)
