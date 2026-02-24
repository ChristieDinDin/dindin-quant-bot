# 🚀 DinDin Quant Bot

A professional-grade quantitative trading bot for Taiwan stock market with clean architecture and automated trading capabilities.

## 📋 Overview

DinDin Quant Bot is a sophisticated trading system designed for algorithmic trading in Taiwan's stock market. It features:

- **Clean Architecture**: Modular design with clear separation of concerns
- **Multiple Data Sources**: Support for yfinance, Shioaji, and future Taiwan bank APIs
- **Extensible Strategy System**: Easy to add and test new trading strategies
- **Comprehensive Backtesting**: Full backtesting engine with optimization
- **Interactive Dashboard**: Real-time monitoring and analysis with Streamlit
- **Production Ready**: Logging, configuration management, error handling

## 🏗️ Architecture

```
src/
├── core/              # Domain layer (business logic)
│   ├── models/        # Data models (OHLCV, Signal, Position)
│   ├── indicators/    # Technical indicators (MFI, RSI, etc.)
│   └── strategies/    # Trading strategies
├── infrastructure/    # External dependencies
│   ├── data_providers/  # yfinance, Shioaji, bank APIs
│   └── database/        # SQLite repository
├── application/       # Use cases and services
│   ├── services/      # Business logic orchestration
│   └── use_cases/     # Specific workflows
├── presentation/      # UI layer
│   ├── dashboard/     # Streamlit web app
│   └── cli/          # Command-line interface
└── utils/            # Shared utilities
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <your-repo>
cd DinDin_Quant_Bot

# Create virtual environment
python -m venv quant_env
source quant_env/bin/activate  # On Windows: quant_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Database

```bash
python scripts/setup_db.py
```

### 3. Fetch Data

```bash
# Fetch historical data for Taiwan stocks
python scripts/fetch_historical_data.py 2337.TW 6944.TW --days 365
```

### 4. Run Dashboard

```bash
streamlit run src/presentation/dashboard/app.py
```

The dashboard will open in your browser at `http://localhost:8501`

### 5. Deploy to Cloud (Optional)

Run the dashboard **without localhost** – deploy to Streamlit Community Cloud. Access from any device, no need to keep your computer on.

**See [DEPLOY_STREAMLIT_CLOUD.md](DEPLOY_STREAMLIT_CLOUD.md)** for full instructions.

## 📊 Features

### Current Implementation

- ✅ **MFI Hunter Strategy**: Momentum-based strategy using Money Flow Index
  - Tiered position sizing
  - Risk management with max position limits
  - Optimized for Taiwan market

- ✅ **Data Management**:
  - Historical data fetching and caching
  - SQLite database for persistence
  - Support for multiple data providers

- ✅ **Backtesting**:
  - Full backtesting engine using backtesting.py
  - Parameter optimization
  - Performance metrics (Sharpe, Sortino, Calmar ratios)

- ✅ **Interactive Dashboard**:
  - Real-time strategy parameters tuning
  - Performance visualization
  - Trading signal recommendations

### 🔮 Future Enhancements

1. **Taiwan Bank API Integration**: Direct integration with Taiwan financial institutions
2. **Advanced Strategies**: Machine learning models, multi-factor strategies
3. **Live Trading**: Automated order execution via Shioaji
4. **Risk Management**: Portfolio-level risk controls, stop-losses
5. **Alerts & Notifications**: Email/SMS alerts for signals
6. **Multi-timeframe Analysis**: Analyze multiple timeframes simultaneously

## 📖 Usage

### Running Backtests

```bash
# Single backtest
python -c "
from src.application.use_cases.run_backtest import RunBacktestUseCase
from src.application.services.backtest_service import BacktestService
from src.application.services.data_service import DataService
from src.infrastructure.data_providers.yfinance_provider import YFinanceProvider
from src.infrastructure.database.connection import get_database
from src.infrastructure.database.repository import MarketDataRepository

provider = YFinanceProvider()
provider.connect()
db = get_database()
repository = MarketDataRepository(db)
data_service = DataService(provider, repository)
backtest_service = BacktestService(data_service)
use_case = RunBacktestUseCase(backtest_service, data_service)

result = use_case.execute(
    symbol='2337.TW',
    strategy_name='mfi_hunter'
)
print(result)
"

# Batch backtesting with optimization
python scripts/run_batch_backtest.py 2337.TW 6944.TW --optimize
```

### Creating Custom Strategies

```python
from src.core.strategies.base import MomentumStrategy
from src.core.models.signal import TradingSignal, SignalType, SignalStrength
from decimal import Decimal

class MyCustomStrategy(MomentumStrategy):
    def __init__(self, param1: int = 10):
        super().__init__("My Strategy", "Custom trading strategy")
        self.param1 = param1
    
    def initialize(self, df):
        # Calculate indicators
        pass
    
    def generate_signal(self, df, index=-1):
        # Your signal logic
        return TradingSignal(...)
    
    def get_position_size(self, current_equity, current_price, signal):
        # Position sizing logic
        return int(current_equity * 0.1 / current_price)

# Register your strategy
from src.core.strategies.registry import get_global_registry
registry = get_global_registry()
registry.register('my_custom_strategy', MyCustomStrategy, 'Description')
```

## 🔧 Configuration

Configuration files are in `config/`:

- `default.yaml`: Base configuration
- `development.yaml`: Dev environment overrides
- `production.yaml`: Production settings

Environment variables:

```bash
export ENVIRONMENT=production
export DATA_PROVIDER=yfinance
export SHIOAJI_API_KEY=your_api_key
export SHIOAJI_SECRET_KEY=your_secret_key
```

## 🎯 Trading Strategies

### MFI Hunter Strategy

Money Flow Index-based momentum strategy:

- **Buy Signal**: MFI < 35 (15% position)
- **Strong Buy**: MFI < 20 (30% position)
- **Sell Signal**: MFI > 85 (close all positions)
- **Max Position**: 80% of equity

Configure in `config/strategies/mfi_hunter.yaml`

## 📈 Performance Metrics

The system tracks:

- **Return Metrics**: Total return, buy & hold return
- **Risk Metrics**: Max drawdown, Sharpe ratio, Sortino ratio, Calmar ratio
- **Trade Statistics**: Win rate, number of trades, best/worst trades
- **Exposure**: Time in market percentage

## 🛡️ Risk Management

Built-in risk controls:

- Maximum position size limits
- Tiered position sizing
- Strategy-level risk parameters
- Portfolio-level tracking (future)

## 🔐 Security

- Never commit credentials to git (use `.env` files)
- Use simulation mode for testing
- Implement proper order validation
- Monitor position sizes and portfolio risk

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Full test suite
pytest tests/
```

## 📚 Documentation

Additional documentation in `docs/`:

- `ARCHITECTURE.md`: Detailed architecture explanation
- `STRATEGIES.md`: Strategy development guide
- `API.md`: API reference

## 🤝 Contributing

This is a personal project, but feedback and suggestions are welcome!

## 📄 License

Private project - All rights reserved

## 🙏 Acknowledgments

- **pandas_ta**: Technical analysis library
- **backtesting.py**: Backtesting framework
- **Shioaji**: Taiwan securities API
- **Streamlit**: Dashboard framework

## 📞 Support

For questions or issues, please open an issue in the repository.

---

**Disclaimer**: This software is for educational and research purposes. Use at your own risk. Past performance does not guarantee future results. Always test thoroughly before live trading.
