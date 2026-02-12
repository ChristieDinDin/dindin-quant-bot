"""
Watchlist management utility.
Allows users to save their favorite stocks for quick access.
"""
import yaml
from pathlib import Path
from typing import List, Dict


WATCHLIST_FILE = Path("data/user_watchlist.yaml")


def load_watchlist() -> List[str]:
    """
    Load user's custom watchlist.
    
    Returns:
        List of stock symbols in watchlist
    """
    if not WATCHLIST_FILE.exists():
        # Return default watchlist
        return ["2330.TW", "2454.TW", "2317.TW", "2337.TW", "6944.TW"]
    
    try:
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data.get('watchlist', [])
    except Exception as e:
        print(f"Error loading watchlist: {e}")
        return ["2330.TW", "2454.TW", "2317.TW"]


def save_watchlist(symbols: List[str]) -> bool:
    """
    Save watchlist to file.
    
    Args:
        symbols: List of stock symbols
        
    Returns:
        True if successful
    """
    try:
        # Ensure directory exists
        WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to YAML
        with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
            yaml.dump({'watchlist': symbols}, f, allow_unicode=True)
        
        return True
    except Exception as e:
        print(f"Error saving watchlist: {e}")
        return False


def add_to_watchlist(symbol: str) -> bool:
    """
    Add a stock to watchlist.
    
    Args:
        symbol: Stock symbol to add
        
    Returns:
        True if added (or already exists)
    """
    watchlist = load_watchlist()
    
    if symbol not in watchlist:
        watchlist.append(symbol)
        return save_watchlist(watchlist)
    
    return True  # Already in watchlist


def remove_from_watchlist(symbol: str) -> bool:
    """
    Remove a stock from watchlist.
    
    Args:
        symbol: Stock symbol to remove
        
    Returns:
        True if removed successfully
    """
    watchlist = load_watchlist()
    
    if symbol in watchlist:
        watchlist.remove(symbol)
        return save_watchlist(watchlist)
    
    return True  # Not in watchlist anyway


def is_in_watchlist(symbol: str) -> bool:
    """
    Check if symbol is in watchlist.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        True if in watchlist
    """
    watchlist = load_watchlist()
    return symbol in watchlist
