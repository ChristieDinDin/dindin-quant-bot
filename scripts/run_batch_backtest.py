#!/usr/bin/env python3
"""
Batch backtesting script.

Run backtests on multiple symbols or with parameter optimization.
"""
import sys
from pathlib import Path
import argparse
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.application.use_cases.run_backtest import RunBacktestUseCase
from src.application.services.backtest_service import BacktestService
from src.application.services.data_service import DataService
from src.infrastructure.data_providers.yfinance_provider import YFinanceProvider
from src.infrastructure.database.connection import get_database
from src.infrastructure.database.repository import MarketDataRepository
from src.utils.logger import get_logger, Logger
from src.utils.config import get_config

logger = get_logger(__name__)


def main():
    """Run batch backtests."""
    parser = argparse.ArgumentParser(description='Run batch backtests')
    parser.add_argument('symbols', nargs='+', help='Stock symbols to test')
    parser.add_argument('--strategy', default='mfi_hunter', help='Strategy name')
    parser.add_argument('--optimize', action='store_true', help='Run parameter optimization')
    parser.add_argument('--output', default='output/backtests/results.csv', help='Output file')
    
    args = parser.parse_args()
    
    print("🔬 DinDin Quant Bot - Batch Backtesting")
    print("=" * 50)
    
    # Load config
    config = get_config()
    Logger.configure(config.logging)
    
    # Initialize services
    provider = YFinanceProvider()
    provider.connect()
    
    db = get_database(config.database.path)
    repository = MarketDataRepository(db)
    
    data_service = DataService(provider, repository)
    backtest_service = BacktestService(data_service)
    use_case = RunBacktestUseCase(backtest_service, data_service)
    
    print(f"\n📊 Testing {len(args.symbols)} symbols")
    print(f"🎯 Strategy: {args.strategy}")
    print(f"⚙️  Optimization: {'Enabled' if args.optimize else 'Disabled'}\n")
    
    results = []
    
    # Run backtests
    for i, symbol in enumerate(args.symbols, 1):
        print(f"[{i}/{len(args.symbols)}] Testing {symbol}...")
        
        try:
            if args.optimize:
                # Run optimization
                result = use_case.execute_optimization(
                    symbol=symbol,
                    strategy_name=args.strategy,
                    param_ranges={
                        'mfi_period': range(10, 25, 2),
                        'buy_threshold': range(25, 45, 5),
                        'sell_threshold': range(75, 95, 5),
                    }
                )
            else:
                # Run single backtest
                result = use_case.execute(
                    symbol=symbol,
                    strategy_name=args.strategy
                )
            
            if result['success']:
                results.append(result)
                print(f"  ✓ Return: {result['return_pct']:.2f}%, "
                      f"Win Rate: {result['win_rate_pct']:.1f}%")
            else:
                print(f"  ✗ Failed: {result['error']}")
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    # Save results
    if results:
        df = pd.DataFrame(results)
        
        # Create output directory
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Select key columns
        columns = ['symbol', 'strategy', 'return_pct', 'win_rate_pct', 
                  'num_trades', 'sharpe_ratio', 'max_drawdown_pct']
        
        if args.optimize:
            columns.append('optimized_params')
        
        available_cols = [col for col in columns if col in df.columns]
        df[available_cols].to_csv(output_path, index=False)
        
        print(f"\n📁 Results saved to: {output_path}")
        
        # Summary
        print("\n" + "=" * 50)
        print("Summary Statistics:")
        print(f"  Average Return: {df['return_pct'].mean():.2f}%")
        print(f"  Average Win Rate: {df['win_rate_pct'].mean():.1f}%")
        print(f"  Best Performer: {df.loc[df['return_pct'].idxmax(), 'symbol']}")
        print("=" * 50)


if __name__ == '__main__':
    main()
