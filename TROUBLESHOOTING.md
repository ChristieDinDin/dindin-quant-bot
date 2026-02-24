# 🔧 Troubleshooting Guide

Common issues and solutions for DinDin Quant Bot.

---

## 📊 **Dashboard Issues**

### **"Strategy not found" Error**

**Symptom**: Error message saying strategy not available

**Cause**: Streamlit is caching old modules

**Solutions:**

1. **Clear Streamlit Cache** (Easiest):
   - Press `C` in the terminal running Streamlit
   - Or press "Clear Cache" button in dashboard menu (top-right)

2. **Restart Dashboard**:
   ```bash
   # Press Ctrl+C to stop
   ./run_dashboard.sh  # Restart
   ```

3. **Hard Refresh**:
   ```bash
   # Kill all Streamlit processes
   pkill -f streamlit
   
   # Restart
   ./run_dashboard.sh
   ```

### **"Backtest Failed" Error**

**Symptom**: Red error box in "Risk & Reward" section

**Common Causes:**

1. **No data for symbol**
   - Solution: Run `python scripts/fetch_historical_data.py SYMBOL.TW`

2. **Insufficient data points**
   - Need at least 100 days for meaningful backtest
   - Solution: Fetch more historical data

3. **Invalid parameters**
   - Period too large for dataset
   - Solution: Reduce indicator periods

### **RSI + MFI Shows 0 Trades**

**This is NOT an error!** The consensus strategy is very selective.

**Why 0 trades?**
- Strategy requires BOTH RSI and MFI to be oversold simultaneously
- In trending markets, indicators may not align
- This is a feature (prevents false signals), not a bug

**Solutions to get more trades:**

1. **Relax Thresholds** (Recommended):
   ```
   RSI Oversold: 40 (instead of 30)
   MFI Oversold: 45 (instead of 35)
   ```

2. **Test on Different Symbol**:
   - Switch to 2337.TW
   - Different stocks have different behavior

3. **Try Different Time Periods**:
   - Fetch longer historical data
   - Test on different market conditions

---

## 💾 **Data Issues**

### **"No data available for symbol"**

**Solutions:**

1. **Check if data exists**:
   ```bash
   python -c "
   from src.infrastructure.database.connection import get_database
   from src.infrastructure.database.repository import MarketDataRepository
   
   db = get_database()
   repo = MarketDataRepository(db)
   symbols = repo.get_all_symbols()
   print('Available symbols:', symbols)
   "
   ```

2. **Fetch data**:
   ```bash
   python scripts/fetch_historical_data.py YOUR_SYMBOL.TW --days 365
   ```

3. **Re-run migration**:
   ```bash
   python scripts/migrate_old_data.py
   ```

### **Data Seems Outdated**

**Solution - Force Refresh:**
```bash
python scripts/fetch_historical_data.py 6944.TW 2337.TW --days 365
```

---

## 🔌 **Installation Issues**

### **"Module not found" Errors**

**Solution:**
```bash
source quant_env/bin/activate
pip install -r requirements.txt
```

### **pandas_ta Import Errors**

The project uses `pandas-ta-classic`. If you see errors:

```bash
pip uninstall pandas-ta pandas-ta-classic
pip install git+https://github.com/freqtrade/pandas-ta@main
```

### **NumPy 2.0 Compatibility Warning**

This is handled automatically in the code. Ignore warnings about `np.bool8`.

---

## 🐛 **Common Errors**

### **"ImportError: attempted relative import"**

**Cause**: Running Python files directly instead of through proper entry points

**Solution**: Use the launcher scripts:
```bash
./run_dashboard.sh  # Instead of: python src/presentation/dashboard/app.py
```

### **"Backtest(...) got unexpected keyword"**

**Cause**: Backtesting library version mismatch

**Solution**:
```bash
pip install --upgrade backtesting
# Or pin to specific version:
pip install backtesting==0.6.5
```

### **"Database is locked"**

**Cause**: Multiple processes accessing database

**Solution**:
```bash
# Close all Python processes
pkill -f python

# Restart dashboard
./run_dashboard.sh
```

---

## 📈 **Performance Issues**

### **Dashboard Loads Slowly**

**Causes & Solutions:**

1. **Large dataset**: 
   - Limit data range in `data_service.py`
   - Use sampling for visualization

2. **Too many calculations**:
   - Indicators are recalculated on each slider change
   - This is normal for real-time updates

3. **Database query slow**:
   - Add more indexes (already done)
   - Use SSD for database

### **Backtest Takes Long Time**

**Normal behavior for:**
- Long historical periods (>1000 days)
- Complex strategies
- Parameter optimization

**To speed up:**
- Reduce data range
- Use fewer optimization iterations
- Test on smaller datasets first

---

## 🧪 **Testing & Validation**

### **How to Verify Everything Works**

**Quick Test Script:**
```bash
cd /Users/dindin/Desktop/DinDin_Quant_Bot
source quant_env/bin/activate

# Test 1: Database
python -c "
from src.infrastructure.database.connection import get_database
db = get_database()
print('✅ Database OK:', db.get_tables())
"

# Test 2: Data Loading
python -c "
from src.infrastructure.database.repository import MarketDataRepository
from src.infrastructure.database.connection import get_database
repo = MarketDataRepository(get_database())
df = repo.get_data('6944.TW')
print('✅ Data OK:', len(df), 'rows')
"

# Test 3: Strategy Registry
python -c "
from src.core.strategies.registry import get_global_registry
registry = get_global_registry()
print('✅ Strategies OK:', registry.list_strategies())
"

# Test 4: Backtest
python -c "
from src.application.use_cases.run_backtest import RunBacktestUseCase
from src.application.services.backtest_service import BacktestService
from src.application.services.data_service import DataService
from src.infrastructure.data_providers.yfinance_provider import YFinanceProvider
from src.infrastructure.database.connection import get_database
from src.infrastructure.database.repository import MarketDataRepository

provider = YFinanceProvider()
provider.connect()
repo = MarketDataRepository(get_database())
data_service = DataService(provider, repo)
backtest_service = BacktestService(data_service)
use_case = RunBacktestUseCase(backtest_service, data_service)

result = use_case.execute('6944.TW', 'mfi_hunter')
print('✅ Backtest OK:', result['success'])
"
```

If all print "✅ OK", your system is working correctly!

---

## 🔄 **Streamlit-Specific Issues**

### **Cache Problems**

Streamlit aggressively caches. To clear:

1. **In Terminal**: Press `C` (while Streamlit is running)
2. **In Browser**: Click menu (☰) → "Clear cache"
3. **Hard Reset**: Restart terminal + browser

### **Hot Reload Not Working**

Streamlit should auto-reload when files change, but sometimes doesn't:

**Solution**: Add to `.streamlit/config.toml`:
```toml
[server]
runOnSave = true

[runner]
fastReruns = true
```

---

## 📁 **File Structure Issues**

### **Can't Find Module**

**Cause**: Python path not set correctly

**Solution**: Always run from project root:
```bash
cd /Users/dindin/Desktop/DinDin_Quant_Bot
./run_dashboard.sh
```

### **Import Errors**

All imports should be absolute (starting with `src.`):
```python
# ✅ Good
from src.core.strategies.mfi_hunter import MfiHunterStrategy

# ❌ Bad (will break)
from ...core.strategies.mfi_hunter import MfiHunterStrategy
```

---

## 🆘 **Still Having Issues?**

### **Debug Mode**

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
./run_dashboard.sh
```

### **Check System Health**

Run the comprehensive test:
```bash
python scripts/run_batch_backtest.py 6944.TW
```

If this works, dashboard should work too!

### **Nuclear Option** (Reset Everything)

```bash
# Backup your data
cp -r data/database data/database_backup

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Restart
./run_dashboard.sh
```

---

## 💬 **Getting Help**

If problems persist:

1. **Check the error message** - Often self-explanatory
2. **Read the stack trace** - Shows exactly where it failed
3. **Test components individually** - Use test scripts
4. **Check documentation** - `docs/` folder
5. **Review recent changes** - Use git to see what changed

---

## ✅ **Prevention Tips**

1. **Always use virtual environment**:
   ```bash
   source quant_env/bin/activate
   ```

2. **Run from project root**:
   ```bash
   cd /Users/dindin/Desktop/DinDin_Quant_Bot
   ```

3. **Clear cache when adding new strategies**:
   - Press `C` in Streamlit terminal

4. **Test new code before adding to dashboard**:
   - Write test scripts first
   - Verify in isolation
   - Then integrate

5. **Keep data up-to-date**:
   - Fetch fresh data weekly
   - Monitor data quality

---

**Most issues are resolved by:**
1. Restarting dashboard
2. Clearing Streamlit cache
3. Running from correct directory

Happy trading! 🚀
