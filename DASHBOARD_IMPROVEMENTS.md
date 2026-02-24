# Dashboard Improvements - Capital Display & RSI Visualization

## Changes Made

### 1. Capital & P/L Display ✅

**File: `src/presentation/dashboard/components/metrics.py`**

Added a new section showing absolute capital values:

- **初始資金 (Initial Capital)**: Shows starting capital (e.g., 1,000,000 TWD)
- **最終資金 (Final Value)**: Shows final portfolio value with profit delta
- **淨利潤 (Net Profit)**: Shows absolute profit/loss in TWD
- **歷史最高 (Peak Value)**: Shows highest portfolio value during backtest

**Why**: Percentage returns are good, but traders need to see actual money amounts to understand real gains/losses.

### 2. RSI Overlay Chart ✅

**File: `src/presentation/dashboard/components/charts.py`**

Created new `create_price_mfi_rsi_chart()` function:

- **MFI Line**: Primary indicator (purple, solid)
- **RSI Line**: Overlay indicator (green, dotted)
- **Consensus Buy/Sell**: Star markers when BOTH indicators agree
- **Threshold zones**: Visual zones for overbought/oversold
- **Threshold lines**: Dotted lines for RSI thresholds

**Why**: For divergence detection, you need to see both indicators on the same chart to compare their movements directly.

### 3. Dynamic Chart Selection ✅

**File: `src/presentation/dashboard/app.py`**

Dashboard now:
- Uses `create_price_mfi_chart()` for MFI Hunter strategy
- Uses `create_price_mfi_rsi_chart()` for RSI+MFI Consensus strategy
- Automatically calculates RSI if needed
- Passes initial capital to metrics display

## Usage

### MFI Hunter Strategy
Shows traditional MFI chart with:
- Price candlesticks (top)
- MFI indicator (bottom)
- Buy/Sell signals based on MFI thresholds

### RSI + MFI Consensus Strategy
Shows combined chart with:
- Price candlesticks (top)
- MFI (purple solid line) + RSI (green dotted line) overlaid (bottom)
- **⭐ Consensus signals**: Stars appear when both indicators agree
  - Green star: Both oversold (strong buy)
  - Red star: Both overbought (strong sell)

## Design Rationale

### Overlay vs Separate Subplots
**Choice: Overlay** ✅

Advantages:
- Direct visual comparison of MFI vs RSI
- Easy to spot divergence (when one goes up, other goes down)
- Less scrolling, more compact
- Thresholds for both visible simultaneously

Use case: In divergence trading, you're looking for moments when RSI and MFI disagree (e.g., RSI rising but MFI falling). Overlay makes this pattern immediately visible.

## Testing

Restart dashboard:
```bash
./run_dashboard.sh
```

1. **Test Capital Display**: 
   - Select any strategy
   - Check bottom metrics section
   - Should see 4 new capital metrics with TWD amounts

2. **Test RSI+MFI Chart**:
   - Select "RSI+MFI Consensus (雙重共識)" strategy
   - Chart should show both purple (MFI) and green dotted (RSI) lines
   - Look for star markers where both agree
   - Adjust RSI/MFI thresholds to see different signals

## Future Enhancements

- [ ] Equity curve chart (show portfolio value over time)
- [ ] Trade markers on price chart
- [ ] Zoom/date range selector
- [ ] Export backtest results to CSV
- [ ] Compare multiple strategies side-by-side
