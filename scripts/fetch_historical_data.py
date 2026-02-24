#!/usr/bin/env python3
"""
Fetch historical data script.

Download and store historical market data for specified symbols.
"""
import sys
from pathlib import Path
from datetime import date, timedelta
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.application.use_cases.fetch_market_data import FetchMarketDataUseCase
from src.application.services.data_service import DataService
from src.infrastructure.data_providers.yfinance_provider import YFinanceProvider
from src.infrastructure.database.connection import get_database
from src.infrastructure.database.repository import MarketDataRepository
from src.utils.logger import get_logger, Logger
from src.utils.config import get_config

logger = get_logger(__name__)


def main():
    """Fetch historical data."""
    parser = argparse.ArgumentParser(description='Fetch historical market data')
    parser.add_argument('symbols', nargs='+', help='Stock symbols to fetch (e.g., 2337.TW 6944.TW)')
    parser.add_argument('--days', type=int, default=365, help='Number of days to fetch (default: 365)')
    parser.add_argument('--force', action='store_true', help='Force refresh (ignore cache)')
    
    args = parser.parse_args()
    
    print("📈 DinDin Quant Bot - Data Fetcher")
    print("=" * 50)
    
    # Load config and setup logging
    config = get_config()
    Logger.configure(config.logging)
    
    # Initialize services
    provider = YFinanceProvider()
    provider.connect()
    
    db = get_database(config.database.path)
    repository = MarketDataRepository(db)
    
    data_service = DataService(provider, repository)
    use_case = FetchMarketDataUseCase(data_service)
    
    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=args.days)
    
    print(f"\n📅 Date range: {start_date} to {end_date}")
    print(f"📊 Symbols: {', '.join(args.symbols)}")
    print(f"🔄 Force refresh: {args.force}\n")
    
    # Fetch data for each symbol
    results = use_case.execute_batch(
        symbols=args.symbols,
        start_date=start_date,
        end_date=end_date
    )
    
    # Display results
    print("\n" + "=" * 50)
    print(f"✅ Completed: {results['successful']}/{results['total']}")
    
    if results['failed'] > 0:
        print(f"❌ Failed: {results['failed']}")
    
    print("\nDetails:")
    for symbol, result in results['results'].items():
        if result['success']:
            print(f"  ✓ {symbol}: {result['rows']} bars, "
                  f"latest close: {result['latest_close']:.2f}")
        else:
            print(f"  ✗ {symbol}: {result['error']}")
    
    print("\n" + "=" * 50)


if __name__ == '__main__':
    main()
