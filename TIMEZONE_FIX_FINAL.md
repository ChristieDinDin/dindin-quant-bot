# Timezone Fix - Clean Architecture Solution

## The Problem
- `yfinance` returns timezone-aware data (Asia/Taipei) for Taiwan stocks
- `backtesting.py` requires timezone-naive data
- We were fighting timezone issues in 10+ places across the codebase

## The Solution - Data Provider Contract

### 1. Added `_normalize_timezone()` to Base DataProvider
**File: `src/infrastructure/data_providers/base.py`**

```python
def _normalize_timezone(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    CRITICAL: Normalize timezone to ensure compatibility with backtesting libraries.
    
    All data providers MUST return timezone-naive DatetimeIndex.
    This method should be called by all concrete providers.
    """
    # Strip timezone from index if present
    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    # Also check datetime columns
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            if hasattr(df[col], 'dt') and hasattr(df[col].dt, 'tz'):
                if df[col].dt.tz is not None:
                    df[col] = df[col].dt.tz_localize(None)
    
    return df
```

### 2. YFinance Provider Calls It
**File: `src/infrastructure/data_providers/yfinance_provider.py`**

In `_clean_dataframe()`:
```python
# CRITICAL: Normalize timezone at the source
df = self._normalize_timezone(df)
```

### 3. Simplified All Downstream Code
- **Indicators (MFI, RSI, MACD)**: Removed all timezone handling
- **BacktestService**: Removed complex timezone stripping logic
- **StrategyAdapter**: Simplified init() and next() methods

## Future-Proof for Shioaji
When you implement `ShioajiProvider`:

```python
class ShioajiProvider(TaiwanMarketProvider):
    def get_historical_data(...):
        # Fetch data from Shioaji
        df = shioaji_api.get_data(...)
        
        # Clean and normalize
        df = self._clean_dataframe(df)
        df = self._normalize_timezone(df)  # ← This line ensures compatibility
        
        return df
```

## Key Benefits
1. **Single Source of Truth**: Timezone normalization happens ONCE at the data provider boundary
2. **Clean Core Domain**: Indicators, strategies, and backtesting never worry about timezones
3. **Future-Proof**: All future data providers (Shioaji, bank APIs) follow the same contract
4. **Maintainable**: Clear separation of concerns

## Contract
**All DataProvider implementations MUST return timezone-naive DatetimeIndex.**

This is enforced by:
- Base class providing `_normalize_timezone()` helper
- Documentation in base class
- Assertions in BacktestService (development safety check)

## Files Changed
- `src/infrastructure/data_providers/base.py` - Added `_normalize_timezone()`
- `src/infrastructure/data_providers/yfinance_provider.py` - Call normalization in `_clean_dataframe()`
- `src/application/services/backtest_service.py` - Simplified, added assertion
- `src/core/indicators/mfi.py` - Removed timezone handling
- `src/core/indicators/rsi.py` - Removed timezone handling
- `src/core/indicators/macd.py` - Removed timezone handling

## Testing
Restart dashboard:
```bash
./run_dashboard.sh
```

Select stock (6944.TW) and strategy (MFI Hunter or RSI + MFI Consensus).
Should work without timezone errors.
