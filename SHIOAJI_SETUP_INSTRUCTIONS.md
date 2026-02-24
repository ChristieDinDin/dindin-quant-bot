# Shioaji Setup Instructions - Step by Step

## 🎯 Overview
You now have a complete Shioaji integration! Follow these steps to set it up safely.

---

## 📋 Step 1: Install Dependencies

```bash
cd /Users/dindin/Desktop/DinDin_Quant_Bot

# Activate your virtual environment
source quant_env/bin/activate

# Install new packages
pip install shioaji python-dotenv

# Or install everything
pip install -r requirements.txt
```

---

## 🔐 Step 2: Set Up Credentials

### Create .env file:
```bash
# Copy the example
cp .env.example .env

# Edit with your real credentials
nano .env  # or use any text editor
```

### Fill in your credentials:
```env
# .env file
ENVIRONMENT=development
DATA_PROVIDER=yfinance  # Keep yfinance for now

# Shioaji Credentials
SHIOAJI_API_KEY=Ao5VWHeBpFfzHGN5JRLKvL1TuXNeeuzYjizNQYWnqbku
SHIOAJI_SECRET_KEY=H52etMJf3xG57LzaVRWq5qZZNUKeoEPeiSUEGo7gYRvg
SHIOAJI_PERSON_ID=A233605401
SHIOAJI_SIMULATION=true  # IMPORTANT: Start with true!

# Other settings
DATABASE_PATH=data/database/market_data.db
INITIAL_CASH=1000000
COMMISSION=0.001425
LOG_LEVEL=INFO
```

### ⚠️ IMPORTANT Security Checks:
```bash
# Verify .env is in .gitignore
cat .gitignore | grep "^\.env$"
# Should show: .env

# NEVER commit .env to Git!
git status  # .env should NOT appear
```

---

## 🧪 Step 3: Test Your Connection

Run the safe test script:

```bash
./scripts/test_shioaji_connection.py
```

**What it does:**
- ✅ Loads credentials from .env
- ✅ Connects in SIMULATION mode (safe!)
- ✅ Tests data fetching (TSMC as example)
- ✅ Verifies timezone handling
- ❌ Does NOT make any trades

**Expected output:**
```
🧪 Shioaji Connection Test
====================================
1️⃣  Checking credentials...
   ✅ API Key: abc123****...
   ✅ Secret Key: xyz789****...
   ✅ Person ID: A123****
   ✅ Mode: Simulation (safe)

2️⃣  Creating Shioaji provider...
   ✅ Provider created

3️⃣  Connecting to Shioaji...
🔌 Connecting to Shioaji (Simulation mode)...
✅ Connected to Shioaji!

4️⃣  Testing data fetch (TSMC - 2330.TW)...
📥 Fetching 2330.TW from Shioaji...
✅ Fetched 5 rows
✅ Columns: ['Open', 'High', 'Low', 'Close', 'Volume']
✅ Latest close: 615.00
✅ Timezone properly stripped

5️⃣  Testing latest price fetch...
   ✅ Latest price: 615.00

✅ ALL TESTS PASSED!
```

---

## 🚀 Step 4: Integration Options

### Option A: Keep yfinance (Recommended for now)
**Use Shioaji only for testing:**
```python
# In your code, keep using yfinance
data_service = DataService(yfinance_provider, repository)

# Test Shioaji separately when needed
from src.infrastructure.data_providers.shioaji_provider import ShioajiProvider
sj_provider = ShioajiProvider(api_key, secret_key, person_id)
sj_provider.connect(simulation=True)
```

### Option B: Hybrid Approach (Best for production)
**yfinance for historical, Shioaji for daily updates:**
```python
# Use yfinance for bulk historical data (free, unlimited)
historical_df = yfinance_provider.get_historical_data("2330.TW", start="2020-01-01")

# Use Shioaji for recent data (1 API call/day)
today_df = shioaji_provider.get_historical_data("2330.TW", start=yesterday, end=today)

# Merge in database
repository.save_dataframe(historical_df)
repository.save_dataframe(today_df)
```

### Option C: Full Shioaji (Future)
**Switch completely to Shioaji:**
```python
# Update .env
DATA_PROVIDER=shioaji

# System will use Shioaji for everything
# (We'll implement this later when you're ready)
```

---

## 📊 Step 5: Rate Limit Guidelines

Your Shioaji provider has built-in rate limiting:

### Current Settings:
```python
_min_request_interval = 0.5  # 500ms between requests
_max_requests_per_hour = 300  # Safety limit
```

### Daily Usage Examples:

#### Safe Daily Update (Recommended):
```python
# Update 100 stocks daily
for symbol in ['2330.TW', '2337.TW', ...]:  # 100 stocks
    df = provider.get_historical_data(
        symbol, 
        start_date=yesterday, 
        end_date=today
    )
    # 100 API calls/day = 0.33% of limit
```

#### Hourly Monitoring (Moderate):
```python
# Update 50 stocks every hour during trading (5 hours)
for symbol in top_50:
    df = provider.get_historical_data(symbol, interval='1h')
    # 50 × 5 = 250 API calls/day = 83% of limit
```

#### Real-time (Use Sparingly):
```python
# Subscribe to 10 stocks for real-time updates
provider.subscribe(['2330.TW', '2337.TW', ...], callback=on_update)
# Continuous stream, monitor your quota!
```

---

## ⚙️ Step 6: Configuration

### Update config files if needed:
```yaml
# config/development.yaml
data_provider:
  type: "yfinance"  # or "shioaji"
  
shioaji:
  simulation: true
  rate_limit:
    min_interval_ms: 500
    max_per_hour: 300
```

---

## 🔄 Step 7: Migration Script (Coming Next)

I'll create a script to help you:
1. Bulk import historical data from yfinance
2. Set up daily Shioaji updates
3. Automate the hybrid approach

**Would you like me to create this now?**

---

## 📝 Troubleshooting

### Error: "Module 'shioaji' not found"
```bash
pip install shioaji
```

### Error: "api_key and secret_key are required"
- Check `.env` file exists
- Check credentials are filled in (not "your_api_key_here")
- Check `.env` is in project root

### Error: "Login failed"
- Verify credentials are correct (copy from Sinopac dashboard)
- Check PERSON_ID matches your account
- Try simulation=true first

### Error: "Rate limit exceeded"
- Wait 1 hour for quota to reset
- Reduce request frequency
- Check `_request_count` in provider

### Warning: "No data returned"
- Might be weekend/holiday
- Check date range is valid
- Try a different stock (2330.TW is always active)

---

## ✅ What's Done:

1. ✅ Full ShioajiProvider implementation
2. ✅ Rate limiting protection
3. ✅ Timezone normalization (strips Asia/Taipei)
4. ✅ Safe test script
5. ✅ Simulation mode by default
6. ✅ Requirements updated

## 🎯 Next Steps (Let me know which you want):

1. **Migration Script**: Bulk import yfinance → daily Shioaji updates
2. **Dashboard Integration**: Add Shioaji status to dashboard
3. **Scheduler**: Automated daily data updates
4. **US Stocks**: Set up yfinance for US market (separate project)

**Which would you like me to implement next?**
