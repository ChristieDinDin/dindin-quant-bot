#!/usr/bin/env python3
"""
Automated test script to debug timezone issues without Streamlit.
Runs backtest directly and shows full traceback.
"""
import sys
sys.path.insert(0, '/Users/dindin/Desktop/DinDin_Quant_Bot')

from src.application.use_cases.run_backtest import RunBacktestUseCase
from src.application.services.backtest_service import BacktestService
from src.application.services.data_service import DataService
from src.infrastructure.data_providers.yfinance_provider import YFinanceProvider
from src.infrastructure.database.connection import get_database
from src.infrastructure.database.repository import MarketDataRepository

print("="*80)
print("AUTOMATED BACKTEST TEST")
print("="*80)

# Initialize services
provider = YFinanceProvider()
provider.connect()
repo = MarketDataRepository(get_database())
data_service = DataService(provider, repo)
backtest_service = BacktestService(data_service)
use_case = RunBacktestUseCase(backtest_service, data_service)

print("\n1. Testing MFI Hunter Strategy...")
print("-"*80)

try:
    result = use_case.execute(
        symbol='6944.TW',
        strategy_name='mfi_hunter',
        strategy_params={'mfi_period': 16, 'buy_threshold': 35, 'sell_threshold': 85}
    )
    
    if result['success']:
        print("✅ SUCCESS!")
        print(f"   Return: {result['return_pct']:.2f}%")
        print(f"   Trades: {result['num_trades']}")
        print(f"   Win Rate: {result.get('win_rate', 0):.1f}%")
        print(f"   Sharpe: {result.get('sharpe_ratio', 0):.2f}")
    else:
        print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
        
except Exception as e:
    print(f"❌ EXCEPTION: {e}")
    import traceback
    print("\nFULL TRACEBACK:")
    print("="*80)
    traceback.print_exc()
    print("="*80)

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
