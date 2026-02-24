# 🏗️ Architecture Documentation

## Overview

DinDin Quant Bot follows **Clean Architecture** principles with clear separation between domain logic, application logic, infrastructure, and presentation layers.

## Design Principles

### 1. Dependency Rule

Dependencies point inward:
```
Presentation → Application → Core (Domain)
      ↓            ↓
  Infrastructure
```

- **Core** (domain) has no dependencies
- **Application** depends only on Core
- **Infrastructure** implements interfaces defined in Core/Application
- **Presentation** depends on Application (not Infrastructure)

### 2. Separation of Concerns

Each layer has a specific responsibility:

- **Core**: Business logic, domain models, strategy algorithms
- **Infrastructure**: External systems (databases, APIs, files)
- **Application**: Use cases, orchestration, services
- **Presentation**: UI, user interaction

### 3. Testability

- Mock infrastructure for unit tests
- Test business logic in isolation
- Integration tests for real components

## Layer Details

### Core Layer (`src/core/`)

**Purpose**: Pure business logic with no external dependencies

#### Models (`models/`)
- `market_data.py`: OHLCV data models
- `signal.py`: Trading signal models
- `position.py`: Position and portfolio tracking

#### Indicators (`indicators/`)
- `base.py`: Abstract indicator interfaces
- `mfi.py`: Money Flow Index implementation
- `calculator.py`: Indicator calculation engine

#### Strategies (`strategies/`)
- `base.py`: Strategy base classes
- `mfi_hunter.py`: MFI-based strategy
- `registry.py`: Strategy discovery and creation

### Infrastructure Layer (`src/infrastructure/`)

**Purpose**: Interface with external systems

#### Data Providers (`data_providers/`)
- `base.py`: Abstract provider interface
- `yfinance_provider.py`: yfinance implementation
- `shioaji_provider.py`: Shioaji implementation (template)

**Why Abstraction**: Easy to swap providers without changing business logic

#### Database (`database/`)
- `connection.py`: Thread-safe connection management
- `repository.py`: Data access layer
- `migrations/`: Schema version control

### Application Layer (`src/application/`)

**Purpose**: Orchestrate business workflows

#### Services (`services/`)
- `data_service.py`: Data fetching and caching
- `backtest_service.py`: Backtesting orchestration

Services coordinate between multiple domain objects and infrastructure.

#### Use Cases (`use_cases/`)
- `fetch_market_data.py`: Data acquisition workflow
- `run_backtest.py`: Backtesting workflow

Use cases represent specific user actions.

### Presentation Layer (`src/presentation/`)

**Purpose**: User interface

#### Dashboard (`dashboard/`)
- `app.py`: Main Streamlit app
- `components/`: Reusable UI components
  - `charts.py`: Chart visualizations
  - `metrics.py`: Performance displays
  - `controls.py`: Input controls

**Why Components**: Reusable, testable UI pieces

### Utilities (`src/utils/`)

Shared utilities across layers:
- `config.py`: Configuration management
- `logger.py`: Logging setup
- `exceptions.py`: Custom exceptions
- `helpers.py`: Common functions

## Data Flow

### Fetching Historical Data

```
User → Dashboard → Use Case → Data Service → Provider → Database
                                   ↓
                              Cache Check
```

1. User requests data in dashboard
2. Use case validates inputs
3. Data service checks cache
4. If cache miss, fetches from provider
5. Stores in database
6. Returns to user

### Running Backtest

```
User → Dashboard → Use Case → Backtest Service
                                   ↓
                              Strategy (Core)
                                   ↓
                              Backtesting Library
                                   ↓
                              Results → UI
```

1. User selects strategy and parameters
2. Use case loads data (via Data Service)
3. Creates strategy instance
4. Backtest service runs simulation
5. Results displayed in dashboard

## Extension Points

### Adding New Data Provider

1. Create class inheriting from `DataProvider`
2. Implement all abstract methods
3. Register in configuration

```python
from src.infrastructure.data_providers.base import DataProvider

class MyProvider(DataProvider):
    def connect(self, **credentials): ...
    def get_historical_data(self, symbol, ...): ...
    # ... implement other methods
```

### Adding New Strategy

1. Inherit from appropriate base class
2. Implement required methods
3. Register in strategy registry

```python
from src.core.strategies.base import MomentumStrategy

class MyStrategy(MomentumStrategy):
    def initialize(self, df): ...
    def generate_signal(self, df, index): ...
    def get_position_size(self, equity, price, signal): ...
```

### Adding New Indicator

1. Inherit from `Indicator` base class
2. Implement calculation logic
3. Register with indicator calculator

```python
from src.core.indicators.base import MomentumIndicator

class RSI(MomentumIndicator):
    def calculate(self, df, **kwargs): ...
    def validate_params(self, **kwargs): ...
```

## Configuration Management

Configuration hierarchy:
1. Environment variables (highest priority)
2. Environment-specific YAML (`production.yaml`)
3. Default YAML (`default.yaml`)

This allows:
- Version control of defaults
- Environment-specific overrides
- Secure credential management

## Error Handling

Custom exceptions in `utils/exceptions.py`:

```
TradingBotException (base)
├── DataException
│   ├── DataNotFoundException
│   └── DataProviderException
├── StrategyException
├── BacktestException
└── TradingException
```

Use specific exceptions for better error handling:
```python
from src.utils.exceptions import DataNotFoundException

try:
    data = provider.get_data(symbol)
except DataNotFoundException:
    # Handle missing data
```

## Logging

Centralized logging configuration:
```python
from src.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Processing data")
logger.error("Failed to connect", exc_info=True)
```

Logs go to:
- Console (for development)
- File (with rotation)

## Testing Strategy

### Unit Tests (`tests/unit/`)
- Test core logic in isolation
- Mock infrastructure dependencies
- Fast, deterministic

### Integration Tests (`tests/integration/`)
- Test with real database
- Test provider integrations
- Slower but realistic

### Example:
```python
def test_mfi_calculation():
    indicator = MFI(period=14)
    df = create_test_dataframe()
    
    result = indicator.calculate(df)
    
    assert len(result) == len(df)
    assert 0 <= result.iloc[-1] <= 100
```

## Performance Considerations

1. **Database Caching**: Reduce API calls
2. **Connection Pooling**: Thread-safe DB access
3. **Lazy Loading**: Load data only when needed
4. **Indicator Caching**: Reuse calculations

## Security

1. **Credentials**: Never in code, use environment variables
2. **Database**: Read-only connections where possible
3. **API Keys**: Encrypted storage (future)
4. **Order Validation**: Multiple checks before execution

## Future Enhancements

1. **Event-Driven Architecture**: Real-time data streaming
2. **Microservices**: Separate backtest/live trading
3. **Message Queue**: Async order processing
4. **API Gateway**: REST API for external access

## References

- Clean Architecture: https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- Hexagonal Architecture: https://alistair.cockburn.us/hexagonal-architecture/
