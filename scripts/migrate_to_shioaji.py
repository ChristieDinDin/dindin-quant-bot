#!/usr/bin/env python3
"""
Data Migration Script: yfinance (historical) → Shioaji (daily updates)

This script helps you transition from yfinance to Shioaji:
1. Uses yfinance for bulk historical data (free, unlimited)
2. Sets up Shioaji for daily incremental updates (rate-limit friendly)
3. Stores everything in your local database

Usage:
    python scripts/migrate_to_shioaji.py --stocks 2330.TW 2337.TW 6944.TW
    python scripts/migrate_to_shioaji.py --all-taiwan  # Fetch all Taiwan stocks
    python scripts/migrate_to_shioaji.py --update      # Daily update mode
"""
import sys
import os
from pathlib import Path
from datetime import date, timedelta, datetime
import argparse
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.data_providers.yfinance_provider import YFinanceProvider
from src.infrastructure.data_providers.shioaji_provider import ShioajiProvider
from src.infrastructure.database.connection import DatabaseConnection
from src.infrastructure.database.repository import MarketDataRepository
from src.application.services.data_service import DataService


def setup_providers():
    """Initialize data providers."""
    # Load environment
    load_dotenv(project_root / '.env')
    
    # yfinance provider (for historical data)
    yf_provider = YFinanceProvider()
    yf_provider.connect()
    
    # Shioaji provider (for daily updates)
    api_key = os.getenv('SHIOAJI_API_KEY')
    secret_key = os.getenv('SHIOAJI_SECRET_KEY')
    person_id = os.getenv('SHIOAJI_PERSON_ID')
    simulation = os.getenv('SHIOAJI_SIMULATION', 'true').lower() == 'true'
    
    sj_provider = ShioajiProvider(api_key, secret_key, person_id)
    
    # Try to connect to Shioaji (optional - will fallback to yfinance if fails)
    try:
        sj_provider.connect(simulation=simulation)
        sj_connected = True
    except Exception as e:
        print(f"⚠️  Shioaji connection failed: {e}")
        print("   Will use yfinance for all data.")
        sj_connected = False
    
    # Database
    db_path = os.getenv('DATABASE_PATH', 'data/database/market_data.db')
    db = DatabaseConnection(db_path)
    repository = MarketDataRepository(db)
    
    return yf_provider, sj_provider, sj_connected, repository


def bulk_import_historical(symbols: list, yf_provider, repository, years: int = 5):
    """
    Bulk import historical data using yfinance.
    
    Args:
        symbols: List of stock symbols (e.g., ['2330.TW', '2337.TW'])
        yf_provider: YFinance provider instance
        repository: Database repository
        years: Number of years of historical data to fetch
    """
    print("\n" + "="*60)
    print(f"📦 BULK IMPORT: {len(symbols)} stocks, {years} years of data")
    print("="*60)
    
    end_date = date.today()
    start_date = end_date - timedelta(days=years * 365)
    
    success_count = 0
    failed = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] {symbol}...")
        
        try:
            # Check if data already exists
            existing = repository.get_data(symbol, start_date, end_date)
            
            if not existing.empty:
                last_date = existing.index[-1].date()
                days_old = (date.today() - last_date).days
                
                if days_old <= 1:
                    print(f"   ✅ Already up-to-date (last: {last_date})")
                    success_count += 1
                    continue
                else:
                    print(f"   📥 Updating from {last_date}...")
                    # Only fetch new data
                    start_date = last_date + timedelta(days=1)
            else:
                print(f"   📥 Fetching full history ({years} years)...")
            
            # Fetch from yfinance
            df = yf_provider.get_historical_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval='1d'
            )
            
            if df.empty:
                print(f"   ⚠️  No data returned (might be delisted)")
                failed.append(symbol)
                continue
            
            # Save to database
            repository.save_dataframe(df, symbol)
            print(f"   ✅ Saved {len(df)} rows to database")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            failed.append(symbol)
    
    # Summary
    print("\n" + "="*60)
    print(f"📊 BULK IMPORT SUMMARY")
    print("="*60)
    print(f"✅ Success: {success_count}/{len(symbols)}")
    if failed:
        print(f"❌ Failed: {len(failed)}")
        print(f"   {', '.join(failed[:10])}" + (" ..." if len(failed) > 10 else ""))
    print()


def daily_update_mixed(symbols: list, sj_provider, sj_connected: bool, repository):
    """
    Daily update: Shioaji for Taiwan stocks (if connected), yfinance for US stocks.
    """
    tw_symbols = [s for s in symbols if is_taiwan_symbol(s)]
    us_symbols = [s for s in symbols if not is_taiwan_symbol(s)]
    
    # Taiwan stocks: Shioaji if connected, else yfinance fallback
    if tw_symbols:
        if sj_connected:
            _daily_update_via_provider(
                tw_symbols, sj_provider, repository,
                "Shioaji (Taiwan)"
            )
        else:
            from src.infrastructure.data_providers.yfinance_provider import YFinanceProvider
            yf = YFinanceProvider()
            yf.connect()
            _daily_update_via_provider(tw_symbols, yf, repository, "yfinance (Taiwan fallback)")
            yf.disconnect()
    
    # US stocks via yfinance (Shioaji doesn't support US)
    if us_symbols:
        from src.infrastructure.data_providers.yfinance_provider import YFinanceProvider
        yf_provider = YFinanceProvider()
        yf_provider.connect()
        _daily_update_via_provider(
            us_symbols, yf_provider, repository,
            "yfinance (US)"
        )
        yf_provider.disconnect()


def _daily_update_via_provider(symbols: list, provider, repository, label: str):
    """Generic daily update for any provider."""
    print("\n" + "="*60)
    print(f"🔄 DAILY UPDATE: {len(symbols)} stocks via {label}")
    print("="*60)
    
    yesterday = date.today() - timedelta(days=1)
    today = date.today()
    
    success_count = 0
    failed = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] {symbol}...")
        
        try:
            existing = repository.get_data(symbol, yesterday, today)
            
            if not existing.empty:
                last_date = existing.index[-1].date()
                if last_date >= yesterday:
                    print(f"   ✅ Already up-to-date (last: {last_date})")
                    success_count += 1
                    continue
            
            print(f"   📥 Fetching {yesterday}...")
            df = provider.get_historical_data(
                symbol=symbol,
                start_date=yesterday,
                end_date=today,
                interval='1d'
            )
            
            if df.empty:
                print(f"   ⚠️  No data (might be weekend/holiday)")
                continue
            
            repository.save_dataframe(df, symbol)
            print(f"   ✅ Updated with {len(df)} rows")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            failed.append(symbol)
    
    print("\n" + "="*60)
    print(f"📊 {label} SUMMARY")
    print("="*60)
    print(f"✅ Success: {success_count}/{len(symbols)}")
    if failed:
        print(f"❌ Failed: {len(failed)}")
        print(f"   {', '.join(failed[:10])}" + (" ..." if len(failed) > 10 else ""))
    print()


def get_all_stocks_from_db() -> list:
    """Get all unique stock symbols from the database."""
    try:
        db_path = os.getenv('DATABASE_PATH', 'data/database/market_data.db')
        db = DatabaseConnection(db_path)
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM daily_kline ORDER BY symbol")
        symbols = [row[0] for row in cursor.fetchall()]
        
        db.close()
        return symbols
    except Exception as e:
        print(f"⚠️  Could not fetch stocks from database: {e}")
        return []


def get_taiwan_top_stocks(n: int = 100) -> list:
    """Get list of top N Taiwan stocks by market cap."""
    # Top 100 Taiwan stocks (TWSE 50 + Mid Cap 50)
    top_stocks = [
        # === Top 50 Blue Chips (TWSE 50) ===
        "2330.TW",  # TSMC 台積電
        "2317.TW",  # Hon Hai 鴻海
        "2454.TW",  # MediaTek 聯發科
        "2881.TW",  # Fubon Financial 富邦金
        "2882.TW",  # Cathay Financial 國泰金
        "2412.TW",  # Chunghwa Telecom 中華電
        "2891.TW",  # CTBC Financial 中信金
        "2886.TW",  # Mega Financial 兆豐金
        "2884.TW",  # E.Sun Financial 玉山金
        "2303.TW",  # UMC 聯電
        "1301.TW",  # Formosa Plastics 台塑
        "1303.TW",  # Nan Ya Plastics 南亞
        "2308.TW",  # Delta Electronics 台達電
        "2002.TW",  # China Steel 中鋼
        "3008.TW",  # LARGAN 大立光
        "2382.TW",  # Quanta 廣達
        "2337.TW",  # Macronix 旺宏
        "6944.TW",  # Zulion 兆聯實業
        "2357.TW",  # ASUS 華碩
        "2379.TW",  # Realtek 瑞昱
        "2327.TW",  # Yageo 國巨
        "2301.TW",  # Lite-On 光寶科
        "2395.TW",  # Advantech 研華
        "3034.TW",  # Novatek 聯詠
        "2409.TW",  # AU Optronics 友達
        "3037.TW",  # Unimicron 欣興
        "2408.TW",  # Nanya Tech 南亞科
        "2912.TW",  # President Chain 統一超
        "5880.TW",  # Taiwan Business Bank 合庫金
        "2885.TW",  # Yuanta Financial 元大金
        "2883.TW",  # China Development 開發金
        "2887.TW",  # Taishin Financial 台新金
        "2890.TW",  # Sinopac Financial 永豐金
        "2892.TW",  # First Financial 第一金
        "2880.TW",  # Hua Nan Financial 華南金
        "2888.TW",  # Shin Kong Financial 新光金
        "1326.TW",  # Formosa Chemicals 台化
        "1216.TW",  # Uni-President 統一
        "2207.TW",  # Hotai Motor 和泰車
        "2105.TW",  # Cheng Shin Rubber 正新
        "2801.TW",  # Chang Hwa Bank 彰銀
        "2353.TW",  # Acer 宏碁
        "2324.TW",  # Compal 仁寶
        "2360.TW",  # Kinpo 致伸
        "2377.TW",  # Microstar 微星
        "2603.TW",  # Evergreen Marine 長榮海運
        "2609.TW",  # Yang Ming Marine 陽明
        "2615.TW",  # Wan Hai Lines 萬海
        "5269.TW",  # Airtac 祥碩
        "3231.TW",  # Wistron 緯創
        
        # === Mid Cap 50 (High Growth Potential) ===
        "6505.TW",  # 台塑化 Formosa Petrochemical
        "2345.TW",  # 智邦 Accton
        "2347.TW",  # 聯強 Synnex
        "2356.TW",  # 英業達 Inventec
        "2352.TW",  # 佳世達 Qisda
        "2354.TW",  # 鴻準 Foxconn Tech
        "2201.TW",  # 裕隆 Yulon Motor
        "2027.TW",  # 大成鋼 Ta Chen Steel
        "2006.TW",  # 東和鋼鐵 Tung Ho Steel
        "2059.TW",  # 川湖 Catcher
        "2049.TW",  # 上銀 Hiwin
        "4938.TW",  # 和碩 Pegatron
        "3045.TW",  # 台灣大 Taiwan Mobile
        "4904.TW",  # 遠傳 Far EasTone
        "2606.TW",  # 裕民 U-Ming Marine
        "2376.TW",  # 技嘉 Gigabyte
        "2504.TW",  # 國產 Kuo Chan
        "2014.TW",  # 中鴻 China Steel Structure
        "9904.TW",  # 寶成 Pou Chen
        "9910.TW",  # 豐泰 Feng Tay
        "1402.TW",  # 遠東新 Far Eastern New Century
        "1590.TW",  # 亞德客-KY Airtac
        "2204.TW",  # 中華 China Motor
        "2371.TW",  # 大同 Tatung
        "3481.TW",  # 群創 Innolux
        "6669.TW",  # 緯穎 Wiwynn
        "6770.TW",  # 力積電 PSMC
        "3711.TW",  # 日月光投控 ASE Technology Holding
        "5871.TW",  # 中租-KY Chailease Holding
        "9921.TW",  # 巨大 Giant Manufacturing
        "2618.TW",  # 長榮航 EVA Airways
        "2610.TW",  # 華航 China Airlines
        "6415.TW",  # 矽力-KY Silergy
        "3704.TW",  # 合勤控 ZyXEL
        "6531.TW",  # 愛普 Epoch
        "3702.TW",  # 大聯大 WPG Holdings
        "4919.TW",  # 新唐 Nuvoton
        "6239.TW",  # 力成 Powertech
        "2603.TW",  # 長榮 Evergreen
        "8046.TW",  # 南電 Nan Ya PCB
        "2609.TW",  # 陽明 Yang Ming
        "2615.TW",  # 萬海 Wan Hai
        "9945.TW",  # 潤泰新 Ruentex Industries
        "2023.TW",  # 燁輝 Yieh Phui Enterprise
        "1303.TW",  # 南亞 Nan Ya Plastics
        "9914.TW",  # 美利達 Merida
        "2474.TW",  # 可成 Catcher Technology
        "6116.TW",  # 彩晶 Chunghwa Picture Tubes
        "8299.TW",  # 群聯 Phison Electronics
    ]
    return top_stocks[:n]


def get_us_top_stocks(n: int = 100) -> list:
    """Get list of US stocks from us_stocks.yaml (all categories)."""
    import yaml
    us_file = project_root / 'data' / 'us_stocks.yaml'
    symbols = []
    seen = set()
    if us_file.exists():
        with open(us_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        for category in (data or {}).values():
            if isinstance(category, dict):
                for symbol in category.keys():
                    if symbol not in seen:
                        seen.add(symbol)
                        symbols.append(symbol)
    # Fallback if YAML empty
    if not symbols:
        symbols = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "MU", "CRWD",
            "JPM", "V", "JNJ", "WMT", "PG", "UNH", "HD", "MA", "DIS",
            "BAC", "XOM", "CVX", "KO", "PEP", "COST", "MCD", "NFLX",
            "AMD", "INTC", "CRM", "ORCL", "ADBE", "PYPL", "UBER",
            "SPY", "QQQ", "VOO", "VTI", "IWM", "DIA",
        ]
    return symbols[:n]


def is_taiwan_symbol(symbol: str) -> bool:
    """Check if symbol is a Taiwan stock (Shioaji supports these)."""
    return symbol.endswith('.TW') or symbol.endswith('.TWO')


def main():
    parser = argparse.ArgumentParser(description='Migrate data from yfinance to Shioaji')
    parser.add_argument('--stocks', nargs='+', help='List of stock symbols (e.g., 2330.TW AAPL)')
    parser.add_argument('--all-taiwan', action='store_true', help='Fetch top Taiwan stocks (use --count to specify)')
    parser.add_argument('--all-us', action='store_true', help='Fetch top US stocks for backtesting/monitoring (yfinance)')
    parser.add_argument('--count', type=int, default=50, help='Number of stocks for --all-taiwan or --all-us')
    parser.add_argument('--update', action='store_true', help='Daily update (Shioaji for TW, yfinance for US)')
    parser.add_argument('--years', type=int, default=5, help='Years of historical data (default: 5)')
    
    args = parser.parse_args()
    
    # Determine stock list
    if args.stocks:
        symbols = args.stocks
    elif args.all_taiwan:
        symbols = get_taiwan_top_stocks(args.count)
    elif args.all_us:
        symbols = get_us_top_stocks(args.count)
    elif args.update:
        # Update mode without specific stocks - update ALL stocks in database
        symbols = get_all_stocks_from_db()
        if not symbols:
            print("⚠️  No stocks found in database. Using default stocks.")
            symbols = ["6944.TW", "2337.TW", "2330.TW"]
    else:
        # Default: your current stocks
        symbols = ["6944.TW", "2337.TW", "2330.TW"]
    
    print("\n" + "="*60)
    print("🚀 Data Migration Script")
    print("="*60)
    print(f"Mode: {'Daily Update (Shioaji)' if args.update else 'Bulk Import (yfinance)'}")
    print(f"Stocks: {len(symbols)}")
    print(f"List: {', '.join(symbols[:5])}" + (" ..." if len(symbols) > 5 else ""))
    print("="*60)
    
    # Setup
    yf_provider, sj_provider, sj_connected, repository = setup_providers()
    
    # Execute based on mode
    if args.update:
        # Daily update: Shioaji for TW (if connected), yfinance for US
        daily_update_mixed(symbols, sj_provider, sj_connected, repository)
    else:
        # Bulk import mode - use yfinance
        bulk_import_historical(symbols, yf_provider, repository, years=args.years)
    
    # Cleanup
    yf_provider.disconnect()
    if sj_connected:
        sj_provider.disconnect()
    
    print("\n✅ Migration complete!")
    print("\n📝 Next steps:")
    print("   1. Run this script daily with --update flag")
    print("   2. Or set up a cron job: 0 18 * * 1-5 python scripts/migrate_to_shioaji.py --update")
    print("   3. Your dashboard will automatically use the updated data!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
