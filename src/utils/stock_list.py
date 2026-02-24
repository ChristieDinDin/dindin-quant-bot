"""
Stock list management utilities.

Provides functions to get available stocks from database,
load stock metadata, and manage watchlists.
"""
import yaml
from pathlib import Path
from typing import Dict, List, Tuple
import sqlite3


def is_taiwan_symbol(symbol: str) -> bool:
    """Check if symbol is Taiwan stock (.TW or .TWO)."""
    return symbol.endswith('.TW') or symbol.endswith('.TWO')


def is_us_symbol(symbol: str) -> bool:
    """Check if symbol is US stock (no suffix)."""
    return not is_taiwan_symbol(symbol)


def get_available_stocks_from_db(db_path: str = "data/database/market_data.db") -> List[Tuple[str, int, str, str]]:
    """
    Query database to get all available stocks with their data ranges.
    
    Returns:
        List of tuples: (symbol, num_days, first_date, last_date)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                symbol,
                COUNT(*) as days,
                MIN(date) as first_date,
                MAX(date) as last_date
            FROM daily_kline
            GROUP BY symbol
            HAVING days >= 50
            ORDER BY days DESC, symbol
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        return results
    except Exception as e:
        print(f"Warning: Could not query database: {e}")
        return []


def _get_data_dir() -> Path:
    """Get project data directory (works when run from project root or streamlit)."""
    # Try __file__ based path first (works when module is in project)
    base = Path(__file__).resolve().parent.parent.parent
    data_dir = base / 'data'
    if data_dir.exists():
        return data_dir
    # Fallback: cwd when running streamlit from project root
    cwd_data = Path.cwd() / 'data'
    if cwd_data.exists():
        return cwd_data
    # Last resort: assume we're in src/utils, go up to project
    return data_dir


def load_stock_metadata(include_us: bool = True) -> Dict[str, str]:
    """
    Load stock code -> name mapping from YAML files.

    Merges Taiwan + US stock metadata for unified stock selection.

    Args:
        include_us: If True, also load US stocks (default: True)

    Returns:
        Dict mapping stock codes to names (e.g., "2330.TW": "台積電 TSMC", "AAPL": "Apple")
    """
    all_stocks = {}
    data_dir = _get_data_dir()

    def _load_yaml(filepath: Path) -> None:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            for category in (data or {}).values():
                if isinstance(category, dict):
                    all_stocks.update(category)

    # Taiwan stocks
    try:
        _load_yaml(data_dir / 'taiwan_stocks.yaml')
    except Exception as e:
        print(f"Warning: Could not load Taiwan stock metadata: {e}")

    # US stocks
    if include_us:
        try:
            _load_yaml(data_dir / 'us_stocks.yaml')
        except Exception as e:
            print(f"Warning: Could not load US stock metadata: {e}")

        # Fallback if YAML empty (path issue in Streamlit etc)
        us_count = sum(1 for k in all_stocks if not (k.endswith('.TW') or k.endswith('.TWO')))
        if us_count == 0:
            all_stocks.update({
                "AAPL": "Apple Inc.", "MSFT": "Microsoft Corporation", "GOOGL": "Alphabet Inc. (Google)",
                "AMZN": "Amazon.com Inc.", "META": "Meta Platforms Inc.", "NVDA": "NVIDIA Corporation",
                "TSLA": "Tesla Inc.", "NFLX": "Netflix Inc.", "AMD": "Advanced Micro Devices Inc.",
                "MU": "Micron Technology Inc.", "CRWD": "CrowdStrike Holdings Inc.", "PLTR": "Palantir Technologies Inc.",
                "JPM": "JPMorgan Chase & Co.", "V": "Visa Inc.", "JNJ": "Johnson & Johnson", "WMT": "Walmart Inc.",
                "XOM": "Exxon Mobil Corporation", "CVX": "Chevron Corporation", "BAC": "Bank of America Corporation",
                "HD": "The Home Depot Inc.", "MA": "Mastercard Incorporated", "DIS": "The Walt Disney Company",
                "ONDS": "Ondas Holdings Inc.", "ASTR": "Astra Space Inc.", "COIN": "Coinbase Global Inc.",
                "SPY": "SPDR S&P 500 ETF Trust", "QQQ": "Invesco QQQ Trust (Nasdaq 100)", "AVGO": "Broadcom Inc.",
                "QCOM": "Qualcomm Incorporated", "INTC": "Intel Corporation", "CRM": "Salesforce Inc.",
                "ORCL": "Oracle Corporation", "ADBE": "Adobe Inc.", "UBER": "Uber Technologies Inc.",
                "SMCI": "Super Micro Computer Inc.", "MSTR": "MicroStrategy Incorporated", "NET": "Cloudflare Inc.",
                "DDOG": "Datadog Inc.", "PANW": "Palo Alto Networks Inc.", "RIVN": "Rivian Automotive Inc.",
            })

    return all_stocks


def get_stock_display_name(symbol: str, metadata: Dict[str, str] = None) -> str:
    """
    Get formatted display name for a stock.
    
    Args:
        symbol: Stock code (e.g., "2330.TW")
        metadata: Stock metadata dict (optional, will load if not provided)
    
    Returns:
        Formatted string (e.g., "2330.TW - 台積電 TSMC")
    """
    if metadata is None:
        metadata = load_stock_metadata()
    
    name = metadata.get(symbol, "")
    if name:
        return f"{symbol} - {name}"
    else:
        return symbol


def get_stocks_by_category(category: str = "all", market: str = "both") -> Dict[str, str]:
    """
    Get stocks filtered by category.
    
    Args:
        category: Category name ('all', 'blue_chips', 'technology', 'us_tech', 'us_blue_chips', etc.)
        market: 'tw', 'us', or 'both' - which market's metadata to include
    
    Returns:
        Dict of stock code -> name
    """
    result = {}
    
    # Taiwan stocks
    if market in ("both", "tw"):
        try:
            tw_file = Path(__file__).parent.parent.parent / 'data' / 'taiwan_stocks.yaml'
            if tw_file.exists():
                with open(tw_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                if category == "all":
                    for cat in (data or {}).values():
                        if isinstance(cat, dict):
                            result.update(cat)
                elif category in (data or {}):
                    cat_data = data.get(category, {})
                    if isinstance(cat_data, dict):
                        result.update(cat_data)
        except Exception:
            pass
    
    # US stocks (only for us_* categories or "all")
    if market in ("both", "us") and (category == "all" or category.startswith("us_")):
        try:
            us_file = Path(__file__).parent.parent.parent / 'data' / 'us_stocks.yaml'
            if us_file.exists():
                with open(us_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                if category == "all":
                    for cat in (data or {}).values():
                        if isinstance(cat, dict):
                            result.update(cat)
                elif category in (data or {}):
                    cat_data = data.get(category, {})
                    if isinstance(cat_data, dict):
                        result.update(cat_data)
        except Exception:
            pass
    
    return result


def search_stocks(query: str, metadata: Dict[str, str] = None) -> List[str]:
    """
    Search stocks by code or name.
    
    Args:
        query: Search query (code or name)
        metadata: Stock metadata dict
    
    Returns:
        List of matching stock codes
    """
    if metadata is None:
        metadata = load_stock_metadata()
    
    query_upper = query.upper()
    matches = []
    
    for symbol, name in metadata.items():
        # Match symbol code or name
        if query_upper in symbol.upper() or query_upper in name.upper():
            matches.append(symbol)
    
    return matches


def get_watchlist() -> Dict[str, str]:
    """Get user's watchlist from config."""
    return get_stocks_by_category('watchlist')


def add_to_watchlist(symbol: str, name: str = None):
    """
    Add a stock to watchlist.
    
    TODO: Implement persistent watchlist storage
    """
    pass


def remove_from_watchlist(symbol: str):
    """
    Remove a stock from watchlist.
    
    TODO: Implement persistent watchlist storage
    """
    pass
