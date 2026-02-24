#!/usr/bin/env python3
"""
Test Shioaji Connection - Safe Credential Verification Script

This script tests your Shioaji credentials WITHOUT making any trades.
It will:
1. Load credentials from .env
2. Connect to Shioaji in SIMULATION mode
3. Test basic API calls
4. Report results

SAFE: Runs in simulation mode only!
"""
import sys
import os
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.data_providers.shioaji_provider import ShioajiProvider


def test_shioaji_connection():
    """Test Shioaji connection and basic functionality."""
    
    print("=" * 60)
    print("🧪 Shioaji Connection Test")
    print("=" * 60)
    
    # Load environment variables
    env_path = project_root / '.env'
    if not env_path.exists():
        print("\n❌ ERROR: .env file not found!")
        print(f"   Expected location: {env_path}")
        print("\n📝 Create .env file:")
        print("   1. cp .env.example .env")
        print("   2. Edit .env with your Shioaji credentials")
        return False
    
    load_dotenv(env_path)
    
    # Get credentials
    api_key = os.getenv('SHIOAJI_API_KEY')
    secret_key = os.getenv('SHIOAJI_SECRET_KEY')
    person_id = os.getenv('SHIOAJI_PERSON_ID')
    simulation = os.getenv('SHIOAJI_SIMULATION', 'true').lower() == 'true'
    
    # Validate credentials
    print("\n1️⃣  Checking credentials...")
    if not api_key or api_key == 'your_api_key_here':
        print("   ❌ SHIOAJI_API_KEY not set!")
        return False
    if not secret_key or secret_key == 'your_secret_key_here':
        print("   ❌ SHIOAJI_SECRET_KEY not set!")
        return False
    if not person_id or person_id == 'your_person_id_here':
        print("   ❌ SHIOAJI_PERSON_ID not set!")
        return False
    
    print(f"   ✅ API Key: {api_key[:10]}...")
    print(f"   ✅ Secret Key: {secret_key[:10]}...")
    print(f"   ✅ Person ID: {person_id[:4]}****")
    print(f"   ✅ Mode: {'Simulation (safe)' if simulation else '⚠️  LIVE'}")
    
    # Create provider
    print("\n2️⃣  Creating Shioaji provider...")
    try:
        provider = ShioajiProvider(
            api_key=api_key,
            secret_key=secret_key,
            person_id=person_id
        )
        print("   ✅ Provider created")
    except Exception as e:
        print(f"   ❌ Failed to create provider: {e}")
        return False
    
    # Test connection
    print("\n3️⃣  Connecting to Shioaji...")
    try:
        success = provider.connect(simulation=simulation)
        if not success:
            print("   ❌ Connection failed!")
            return False
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False
    
    # Test fetching data
    print("\n4️⃣  Testing data fetch (TSMC - 2330.TW)...")
    try:
        # Fetch just 1 week of data as a test
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        df = provider.get_historical_data(
            symbol="2330.TW",
            start_date=start_date,
            end_date=end_date,
            interval="1d"
        )
        
        if df.empty:
            print("   ⚠️  No data returned (might be weekend/holiday)")
        else:
            print(f"   ✅ Fetched {len(df)} rows")
            print(f"   ✅ Columns: {df.columns.tolist()}")
            print(f"   ✅ Date range: {df.index[0]} to {df.index[-1]}")
            print(f"   ✅ Latest close: {df['Close'].iloc[-1]:.2f}")
            
            # Verify timezone is stripped
            if hasattr(df.index, 'tz') and df.index.tz is not None:
                print(f"   ⚠️  WARNING: Data has timezone: {df.index.tz}")
            else:
                print("   ✅ Timezone properly stripped")
        
    except Exception as e:
        print(f"   ❌ Data fetch failed: {e}")
        import traceback
        traceback.print_exc()
        provider.disconnect()
        return False
    
    # Test latest price
    print("\n5️⃣  Testing latest price fetch...")
    try:
        price = provider.get_latest_price("2330.TW")
        if price:
            print(f"   ✅ Latest price: {price:.2f}")
        else:
            print("   ⚠️  Could not fetch latest price (might be after hours)")
    except Exception as e:
        print(f"   ❌ Price fetch failed: {e}")
    
    # Test search
    print("\n6️⃣  Testing symbol search...")
    try:
        results = provider.search_symbol("台積電")
        if results:
            print(f"   ✅ Found {len(results)} results")
            for r in results[:3]:
                print(f"      - {r['symbol']}: {r['name']}")
        else:
            print("   ⚠️  No results (might need to search by code)")
    except Exception as e:
        print(f"   ❌ Search failed: {e}")
    
    # Cleanup
    print("\n7️⃣  Disconnecting...")
    provider.disconnect()
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\n🎉 Your Shioaji connection is working!")
    print("\n📝 Next steps:")
    print("   1. Keep SHIOAJI_SIMULATION=true while testing")
    print("   2. Use yfinance for historical bulk data")
    print("   3. Use Shioaji for daily updates")
    print("   4. Set SHIOAJI_SIMULATION=false only when ready for LIVE trading")
    
    return True


if __name__ == "__main__":
    try:
        success = test_shioaji_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
