# 🔧 Timezone Fix Applied

## **Problem**
Both strategies were failing with error:
```
Tz-aware datetime.datetime cannot be converted to datetime64 unless utc=True, at position 183
```

This error occurs because the `backtesting.py` library **requires timezone-naive datetimes**, but somewhere in the data pipeline timezone information was being introduced.

---

## **Solutions Applied**

### **1. Added Timezone Stripping Helper**
Created `_ensure_timezone_naive()` method in `BacktestService` that aggressively removes timezone info from:
- DataFrame index
- Any datetime columns

### **2. Modified Strategy Adapter (init/next methods)**
Changed how DataFrames are created from `backtesting._Data`:
- Now uses `np.array()` to convert data (avoids pandas timezone logic)
- Explicitly recreates index as timezone-naive `DatetimeIndex`
- Added error handling with try-except blocks

### **3. Applied Fix at Multiple Layers**
- **Repository layer**: Ensures data from database is timezone-naive
- **Backtest service**: Strips timezones before passing to `Backtest()`
- **Strategy adapter**: Strips timezones when converting `_Data` to DataFrame

---

## **Files Modified**

1. **`src/application/services/backtest_service.py`**
   - Added `_ensure_timezone_naive()` static method
   - Modified `init()` in `StrategyAdapter` 
   - Modified `next()` in `StrategyAdapter`
   - Added timezone stripping before backtest execution

2. **`src/infrastructure/database/repository.py`**
   - Added timezone check in `get_data()` method

3. **`src/presentation/dashboard/app.py`**
   - Added module reload logic to handle Streamlit caching

---

## **Next Steps**

### **Restart Dashboard:**
```bash
# 1. Stop current dashboard (in terminal where it's running)
Ctrl+C

# 2. Restart
./run_dashboard.sh
```

### **Test Both Strategies:**
1. **MFI Hunter** - Should work with default parameters
2. **RSI+MFI Consensus** - May show 0 trades (normal, try relaxing thresholds)

---

## **If You Still See Errors:**

### **Option 1: Clear Browser Cache**
- Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

### **Option 2: Nuclear Reset**
```bash
# Stop dashboard
Ctrl+C

# Clear all Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Restart
./run_dashboard.sh
```

### **Option 3: Check Data**
```bash
source quant_env/bin/activate
python -c "
from src.infrastructure.database.connection import get_database
from src.infrastructure.database.repository import MarketDataRepository

repo = MarketDataRepository(get_database())
df = repo.get_data('6944.TW')
print('Data loaded:', len(df), 'rows')
print('Index tz:', df.index.tz)
"
```

Should print: `Index tz: None` (timezone-naive)

---

## **Technical Details**

### **Why This Happened**

Pandas 2.x has stricter timezone handling than 1.x:
- Cannot mix tz-aware and tz-naive datetimes
- Must be explicit about timezone conversions
- backtesting.py (designed for pandas 1.x) expects naive datetimes

### **The Fix**

We now:
1. Use numpy arrays for numeric data (avoids pandas timezone inference)
2. Explicitly construct timezone-naive DatetimeIndex
3. Strip timezones at every layer (defense in depth)

### **Why Multiple Layers?**

Different code paths can introduce timezone info:
- Database queries (SQLite date parsing)
- Pandas operations (date arithmetic, resampling)  
- Indicator calculations (rolling windows, ewm)
- DataFrame concatenation

By stripping at every layer, we ensure it never reaches `backtesting.py`.

---

## **Expected Behavior After Fix**

### **MFI Hunter:**
- Should backtest successfully
- Will show trades and performance metrics
- Charts will display buy/sell signals

### **RSI+MFI Consensus:**
- Should backtest successfully (no timezone error)
- May show 0 trades with default thresholds
- This is NORMAL - strategy is very selective
- Try: RSI Oversold=40, MFI Oversold=45 for more signals

---

## **Verification**

If you see the "Risk & Reward" section with metrics like:
- Return: X%
- # Trades: Y
- Win Rate: Z%

Then the fix worked! 🎉

---

Last updated: 2026-02-08
