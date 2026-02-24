## 🎯 Strategy Development Guide

This guide explains how to develop, test, and deploy trading strategies in DinDin Quant Bot.

## Strategy Types

The system supports several strategy base classes:

### 1. **MomentumStrategy**
Buy when indicators show oversold, sell when overbought.

Example: MFI Hunter, RSI strategies

### 2. **TrendFollowingStrategy**
Follow market trends using moving averages, MACD, etc.

Example: MA crossover, MACD strategies

### 3. **MeanReversionStrategy**
Buy when price deviates below mean, sell when above.

Example: Bollinger Bands, Z-Score strategies

### 4. **CompositeStrategy**
Combine multiple strategies with weighted voting.

Example: MFI + RSI + MACD consensus

## Creating a New Strategy

### Step 1: Choose Base Class

```python
from src.core.strategies.base import MomentumStrategy
from src.core.models.signal import TradingSignal, SignalType, SignalStrength
from decimal import Decimal
import pandas as pd

class MyStrategy(MomentumStrategy):
    def __init__(self, param1: int = 10, param2: float = 0.5):
        super().__init__(
            name="My Strategy",
            description="Brief description of what this strategy does"
        )
        # Strategy parameters
        self.param1 = param1
        self.param2 = param2
```

### Step 2: Implement Required Methods

#### initialize()
Called once before backtesting starts. Use this to:
- Calculate indicators
- Set up initial state
- Validate data

```python
def initialize(self, df: pd.DataFrame) -> None:
    """Initialize strategy with market data."""
    self.validate_data(df)
    
    # Calculate indicators you need
    # Store in dataframe or internal state
    from src.core.indicators.mfi import MFI
    
    mfi = MFI(period=self.param1)
    df['MFI'] = mfi.calculate(df)
    
    # Set up any state variables
    self._state['position_count'] = 0
```

#### generate_signal()
Called on each bar. Return a TradingSignal or None.

```python
def generate_signal(self, 
                   df: pd.DataFrame, 
                   index: int = -1) -> Optional[TradingSignal]:
    """Generate trading signal for current bar."""
    
    # Get current values
    current_price = df['Close'].iloc[index]
    current_indicator = df['MFI'].iloc[index]
    current_time = df.index[index]
    
    # Skip if indicator not ready
    if pd.isna(current_indicator):
        return None
    
    # Your trading logic here
    if current_indicator < 30:  # Oversold
        return TradingSignal(
            timestamp=current_time,
            symbol=getattr(df, 'symbol', 'UNKNOWN'),
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            price=Decimal(str(current_price)),
            strategy_name=self.name,
            reason=f"Indicator oversold: {current_indicator:.1f}",
            recommended_position_size=Decimal('0.2'),  # 20%
            indicators={'my_indicator': current_indicator}
        )
    
    elif current_indicator > 70:  # Overbought
        return TradingSignal(
            timestamp=current_time,
            symbol=getattr(df, 'symbol', 'UNKNOWN'),
            signal_type=SignalType.SELL,
            strength=SignalStrength.STRONG,
            price=Decimal(str(current_price)),
            strategy_name=self.name,
            reason=f"Indicator overbought: {current_indicator:.1f}",
            indicators={'my_indicator': current_indicator}
        )
    
    return None  # No signal
```

#### get_position_size()
Calculate how many shares to trade.

```python
def get_position_size(self, 
                     current_equity: float,
                     current_price: float,
                     signal: TradingSignal) -> float:
    """Calculate number of shares to trade."""
    
    # Use recommended size from signal
    position_pct = float(signal.recommended_position_size or 0.1)
    
    # Calculate shares
    position_value = current_equity * position_pct
    shares = int(position_value / current_price)
    
    # Taiwan market: round to lots of 1000
    shares = (shares // 1000) * 1000
    
    return max(shares, 0)
```

### Step 3: Register Strategy

```python
from src.core.strategies.registry import get_global_registry

# In your strategy module
def register_strategy():
    registry = get_global_registry()
    registry.register(
        'my_strategy',
        MyStrategy,
        'Description of my strategy'
    )

# Or in registry.py _register_builtin_strategies()
registry.register('my_strategy', MyStrategy, 'Description')
```

### Step 4: Create Configuration

Create `config/strategies/my_strategy.yaml`:

```yaml
strategy_name: "my_strategy"
description: "My custom strategy"

# Parameters
parameters:
  param1: 10
  param2: 0.5

# Optimization ranges
optimization:
  param1:
    min: 5
    max: 20
    step: 1
  param2:
    min: 0.1
    max: 1.0
    step: 0.1
```

## Testing Your Strategy

### 1. Unit Tests

```python
# tests/unit/test_my_strategy.py
import pytest
import pandas as pd
from src.core.strategies.my_strategy import MyStrategy

def create_test_data():
    """Create sample OHLCV data."""
    dates = pd.date_range('2024-01-01', periods=100)
    data = {
        'Open': [100 + i for i in range(100)],
        'High': [105 + i for i in range(100)],
        'Low': [95 + i for i in range(100)],
        'Close': [100 + i for i in range(100)],
        'Volume': [1000000] * 100,
    }
    return pd.DataFrame(data, index=dates)

def test_strategy_initialization():
    strategy = MyStrategy(param1=10)
    df = create_test_data()
    
    strategy.initialize(df)
    
    assert 'MFI' in df.columns

def test_signal_generation():
    strategy = MyStrategy(param1=10)
    df = create_test_data()
    strategy.initialize(df)
    
    signal = strategy.generate_signal(df, index=-1)
    
    # Test signal is generated correctly
    assert signal is None or signal.strategy_name == strategy.name
```

### 2. Backtesting

```python
from src.application.use_cases.run_backtest import RunBacktestUseCase
from src.application.services.backtest_service import BacktestService
from src.application.services.data_service import DataService
# ... initialize services ...

result = use_case.execute(
    symbol='2337.TW',
    strategy_name='my_strategy',
    strategy_params={
        'param1': 10,
        'param2': 0.5
    }
)

print(f"Return: {result['return_pct']:.2f}%")
print(f"Win Rate: {result['win_rate_pct']:.1f}%")
```

### 3. Parameter Optimization

```python
result = use_case.execute_optimization(
    symbol='2337.TW',
    strategy_name='my_strategy',
    param_ranges={
        'param1': range(5, 21, 1),
        'param2': [x/10 for x in range(1, 11)]
    },
    maximize='Sharpe Ratio'
)

print(f"Best params: {result['optimized_params']}")
```

## Best Practices

### 1. Parameter Validation

Always validate parameters in `__init__`:

```python
def __init__(self, period: int = 14):
    if period < 1:
        raise ValueError("Period must be positive")
    if period > 100:
        raise ValueError("Period too large")
    
    super().__init__("My Strategy")
    self.period = period
```

### 2. Indicator Caching

Calculate indicators once in `initialize()`:

```python
def initialize(self, df):
    # Calculate once
    df['MyIndicator'] = self.calculate_indicator(df)
    
    # Don't recalculate in generate_signal()
```

### 3. Position Sizing

Implement proper position sizing:

```python
def get_position_size(self, equity, price, signal):
    # Base size from signal
    base_pct = float(signal.recommended_position_size)
    
    # Adjust for volatility
    volatility_adj = self.calculate_volatility_adjustment()
    
    # Apply max position limit
    final_pct = min(base_pct * volatility_adj, self.max_position_pct)
    
    return int(equity * final_pct / price)
```

### 4. Risk Management

Add risk controls:

```python
def generate_signal(self, df, index):
    # Check risk limits
    if self._state.get('max_drawdown', 0) > 0.2:  # 20% drawdown
        return None  # Stop trading
    
    # Check position limits
    current_position = self._state.get('position_pct', 0)
    if current_position >= self.max_position_pct:
        return None  # Already at max
    
    # Generate signal
    ...
```

### 5. Logging

Use logging for debugging:

```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

def generate_signal(self, df, index):
    indicator_value = df['MyIndicator'].iloc[index]
    
    logger.debug(f"Checking signal at {df.index[index]}, "
                f"indicator={indicator_value:.2f}")
    
    if indicator_value < self.buy_threshold:
        logger.info(f"BUY signal generated at {df['Close'].iloc[index]}")
        return ...
```

## Common Patterns

### Multi-Indicator Strategy

```python
class MultiIndicatorStrategy(Strategy):
    def initialize(self, df):
        # Calculate multiple indicators
        df['MFI'] = MFI(period=14).calculate(df)
        df['RSI'] = RSI(period=14).calculate(df)
        df['MACD'] = MACD().calculate(df)
    
    def generate_signal(self, df, index):
        # Require consensus from multiple indicators
        mfi_signal = df['MFI'].iloc[index] < 30
        rsi_signal = df['RSI'].iloc[index] < 30
        macd_signal = df['MACD'].iloc[index] > 0
        
        # Need at least 2/3 agreement
        signals_count = sum([mfi_signal, rsi_signal, macd_signal])
        
        if signals_count >= 2:
            return TradingSignal(...)
```

### Tiered Entry Strategy

```python
class TieredStrategy(Strategy):
    def generate_signal(self, df, index):
        indicator = df['Indicator'].iloc[index]
        
        # Multiple entry levels
        if indicator < 15:  # Extreme
            position_size = Decimal('0.30')  # 30%
            strength = SignalStrength.VERY_STRONG
        elif indicator < 25:  # Strong
            position_size = Decimal('0.20')  # 20%
            strength = SignalStrength.STRONG
        elif indicator < 35:  # Normal
            position_size = Decimal('0.10')  # 10%
            strength = SignalStrength.MODERATE
        else:
            return None
        
        return TradingSignal(
            recommended_position_size=position_size,
            strength=strength,
            ...
        )
```

### Time-Based Strategy

```python
class TimeBasedStrategy(Strategy):
    def generate_signal(self, df, index):
        current_time = df.index[index]
        
        # Only trade during specific hours
        if current_time.hour < 10 or current_time.hour > 12:
            return None
        
        # Only trade on specific days
        if current_time.weekday() >= 4:  # Skip Fri
            return None
        
        # Your signal logic
        ...
```

## Strategy Performance Metrics

Track these metrics:
- Total Return %
- Win Rate %
- Sharpe Ratio (risk-adjusted return)
- Max Drawdown %
- Number of Trades
- Average Trade %
- Exposure Time %

## Deployment Checklist

Before deploying to production:

- [ ] Backtest on at least 1 year of data
- [ ] Test on multiple symbols
- [ ] Optimize parameters
- [ ] Validate risk controls
- [ ] Test with realistic commission (0.1425% Taiwan)
- [ ] Run stress tests (bear market, high volatility)
- [ ] Document strategy logic
- [ ] Set up monitoring and alerts

## Resources

- Backtesting Library: https://kernc.github.io/backtesting.py/
- Technical Analysis: https://github.com/bukosabino/ta
- Quantitative Trading: https://www.quantstart.com/
