# Quick Fix: initial_capital NameError

## Problem
```python
NameError: name 'initial_capital' is not defined
```

Dashboard crashed when trying to display performance metrics.

## Root Cause
Variable name mismatch:
- Sidebar controls return: `'initial_cash'`
- Dashboard code used: `initial_capital`

## Fix Applied

**File: `src/presentation/dashboard/app.py`**

1. Extract variables from controls:
```python
initial_capital = controls['initial_cash']
commission_rate = controls['commission']
```

2. Pass to backtest use case:
```python
backtest_results = use_case.execute(
    symbol=symbol,
    strategy_name=strategy_name,
    strategy_params=strategy_params,
    cash=initial_capital,           # ← Now uses user's input
    commission=commission_rate       # ← Now uses user's input
)
```

3. Pass to metrics display:
```python
display_performance_metrics(backtest_results, initial_capital=initial_capital)
```

## Result
✅ Dashboard now correctly uses the initial capital from sidebar settings
✅ Backtest respects user's capital and commission settings
✅ Metrics display shows correct TWD amounts based on user's capital

## Test
Restart dashboard and verify:
1. Initial capital slider works (default: 1,000,000 TWD)
2. Commission slider works (default: 0.1425%)
3. Metrics show correct final capital calculations
