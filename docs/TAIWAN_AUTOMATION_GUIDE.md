# 🇹🇼 Taiwan Stock Market Automation Guide

## Overview

This guide provides insights and recommendations for building a fully automated quantitative trading system for Taiwan's stock market.

## Taiwan Market Characteristics

### Market Hours
- **Trading Hours**: 09:00 - 13:30 (Taiwan Time, UTC+8)
- **No Lunch Break**: Continuous trading session
- **Trading Days**: Monday - Friday (excluding public holidays)
- **Settlement**: T+2 (trade plus 2 days)

### Trading Mechanics
- **Lot Size**: 1,000 shares (1 lot) for most stocks
- **Price Tick Size**: Varies by price level
- **Commission**: ~0.1425% one-way (券商手續費)
- **Securities Transaction Tax**: 0.3% on selling (證券交易稅)
- **Daily Limit**: ±10% price movement limit

### Market Structure
1. **TWSE** (Taiwan Stock Exchange): Main board
2. **TPEx** (Taipei Exchange): OTC market
3. **Emerging Stock Market**: Higher volatility, lower liquidity

## Data Sources for Taiwan Market

### 1. **Shioaji (永豐金證券 API)** ⭐ Recommended
**Best for**: Real-time trading and live data

**Features**:
- Official Python API from Sinopac Securities
- Real-time quotes and historical data
- Order execution capabilities
- Market depth information
- Free for account holders

**Setup**:
```python
from src.infrastructure.data_providers.shioaji_provider import ShioajiProvider

provider = ShioajiProvider()
provider.connect(
    api_key='YOUR_API_KEY',
    secret_key='YOUR_SECRET_KEY',
    simulation=True  # Start with simulation!
)

# Get real-time data
df = provider.get_historical_data('2337', start_date=..., end_date=...)
latest_price = provider.get_latest_price('2337')
```

**Getting Started**:
1. Open account with Sinopac Securities (永豐金證券)
2. Apply for API access
3. Get API key and secret
4. Test in simulation mode first

**Documentation**: https://sinotrade.github.io/

### 2. **yfinance** (Current Implementation)
**Best for**: Historical data and backtesting

**Limitations**:
- Not real-time (delayed quotes)
- Rate limits
- May have data gaps
- No order execution

**Good for**: Development and backtesting phase

### 3. **Taiwan Bank APIs** (Future)
Taiwan banks are developing APIs for financial data:

- **Fubon Securities**: https://www.fbs.com.tw/
- **Cathay Securities**: https://www.cathaysec.com.tw/
- **CTBC Securities**: https://www.ctbcsec.com/

**Status**: Limited public access, mostly for institutional clients

### 4. **Taiwan Economic Journal (TEJ)**
**Best for**: Research-grade data

**Features**:
- High-quality historical data
- Fundamental data
- Financial statements
- Market indices

**Cost**: Paid subscription (expensive)

## Architecture for Automated Trading

### Phase 1: Development (Current)
```
yfinance → Database → Backtesting → Dashboard
```
- Use yfinance for historical data
- Develop and test strategies
- Optimize parameters
- Build monitoring dashboard

### Phase 2: Paper Trading
```
Shioaji (Simulation) → Strategy Engine → Order Management → Monitoring
```
- Connect to Shioaji simulation mode
- Test with real-time data
- Validate order logic
- No real money at risk

### Phase 3: Live Trading
```
Shioaji (Live) → Risk Management → Strategy Engine → Order Execution → Monitoring
```
- Start with small capital
- Strict risk controls
- Real-time monitoring
- Alert system

## Key Components for Automation

### 1. **Scheduler** (Not Yet Implemented)
Execute strategies at specific times:

```python
import schedule
import time

def run_daily_strategy():
    """Run strategy at market open."""
    # Your trading logic
    pass

# Schedule for Taiwan market
schedule.every().monday.at("09:00").do(run_daily_strategy)
schedule.every().tuesday.at("09:00").do(run_daily_strategy)
# ... other days

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 2. **Order Management System**
Essential for live trading:

```python
class OrderManager:
    """Manage order lifecycle."""
    
    def __init__(self, provider, risk_manager):
        self.provider = provider
        self.risk_manager = risk_manager
    
    def place_order(self, symbol, action, quantity, price=None):
        # Pre-trade risk checks
        if not self.risk_manager.validate_order(symbol, quantity):
            raise RiskLimitExceededError()
        
        # Place order via provider
        order = self.provider.place_order(
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price
        )
        
        # Track order
        self.track_order(order)
        
        return order
```

### 3. **Risk Management System**
Critical for protecting capital:

```python
class RiskManager:
    """Enforce risk limits."""
    
    def __init__(self, max_position_pct=0.2, max_daily_loss=-0.03):
        self.max_position_pct = max_position_pct
        self.max_daily_loss = max_daily_loss
        self.daily_pnl = 0
    
    def validate_order(self, symbol, quantity, price):
        # Check position size limit
        if self.would_exceed_position_limit(symbol, quantity):
            return False
        
        # Check daily loss limit
        if self.daily_pnl < self.max_daily_loss:
            return False  # Stop trading for the day
        
        # Check available capital
        if not self.has_sufficient_capital(quantity, price):
            return False
        
        return True
```

### 4. **Monitoring & Alerts**
Stay informed of system status:

```python
class AlertSystem:
    """Send alerts for important events."""
    
    def send_alert(self, level, message):
        if level == 'CRITICAL':
            self.send_sms(message)
            self.send_email(message)
        elif level == 'WARNING':
            self.send_email(message)
        
        # Log all alerts
        logger.log(level, message)

# Usage
alerts = AlertSystem()

# Order filled
alerts.send_alert('INFO', 'Order filled: BUY 2337 @ 150')

# Daily loss limit hit
alerts.send_alert('CRITICAL', 'Daily loss limit reached: -3%')

# Connection lost
alerts.send_alert('CRITICAL', 'Lost connection to Shioaji')
```

### 5. **Performance Tracking**
Monitor live performance:

```python
class PerformanceTracker:
    """Track real-time trading performance."""
    
    def __init__(self, initial_capital):
        self.initial_capital = initial_capital
        self.trades = []
        self.positions = {}
    
    def record_trade(self, trade):
        self.trades.append(trade)
        self.update_metrics()
    
    def get_current_metrics(self):
        return {
            'total_return': self.calculate_return(),
            'win_rate': self.calculate_win_rate(),
            'sharpe_ratio': self.calculate_sharpe(),
            'max_drawdown': self.calculate_drawdown(),
        }
```

## Recommended Technology Stack

### Core Components
```yaml
Language: Python 3.10+
Framework: Current clean architecture

Data Storage:
  - SQLite: Local database (current)
  - PostgreSQL: Production database (recommended for live trading)
  - Redis: Real-time caching (optional)

Monitoring:
  - Grafana: Metrics dashboards
  - Prometheus: Metrics collection
  - Sentry: Error tracking

Alerts:
  - Email: SMTP
  - SMS: Twilio
  - Telegram: python-telegram-bot

Scheduling:
  - schedule: Simple Python scheduler
  - APScheduler: Advanced scheduling
  - Celery: Distributed task queue (for complex systems)
```

## Regulatory Considerations

### Taiwan Financial Regulations
1. **Securities and Futures Bureau (SFB)**: Regulatory authority
2. **Algorithmic Trading Registration**: Required for high-frequency trading
3. **Risk Controls**: Mandatory pre-trade risk checks
4. **Market Making**: Separate license required

### Best Practices
- Start with small capital
- Keep detailed trade logs
- Implement kill switch (emergency stop)
- Regular system audits
- Maintain adequate capital reserves

## Security Best Practices

### 1. **API Key Management**
```python
# NEVER hardcode credentials
# ❌ BAD
api_key = "my_secret_key"

# ✅ GOOD
import os
api_key = os.getenv('SHIOAJI_API_KEY')

# ✅ BETTER
from src.utils.config import get_config
config = get_config()
api_key = config.data_provider.shioaji_api_key
```

### 2. **Order Validation**
```python
def validate_order_before_execution(order):
    """Multi-layer validation."""
    
    # Sanity checks
    assert order.quantity > 0
    assert order.price > 0
    assert order.symbol in ALLOWED_SYMBOLS
    
    # Business logic checks
    assert not is_market_closed()
    assert has_sufficient_funds(order)
    assert not exceeds_position_limit(order)
    
    # Risk checks
    assert not exceeds_daily_loss_limit()
    assert not too_many_trades_today()
```

### 3. **System Monitoring**
```python
class SystemHealthChecker:
    """Monitor system health."""
    
    def check_health(self):
        checks = {
            'database': self.check_database_connection(),
            'data_provider': self.check_data_provider(),
            'disk_space': self.check_disk_space(),
            'memory': self.check_memory_usage(),
            'network': self.check_network_connectivity(),
        }
        
        # Alert if any check fails
        for check, status in checks.items():
            if not status:
                self.send_alert(f'{check} health check failed')
```

## Deployment Strategy

### Development Environment
```bash
# Local development
ENVIRONMENT=development python src/presentation/dashboard/app.py
```

### Staging Environment (Paper Trading)
```bash
# Test with real-time data, no real orders
ENVIRONMENT=staging
SHIOAJI_SIMULATION=true
python scripts/run_live_trader.py
```

### Production Environment (Live Trading)
```bash
# Real money, real orders - be careful!
ENVIRONMENT=production
SHIOAJI_SIMULATION=false  # DANGER!
python scripts/run_live_trader.py
```

## Next Steps Roadmap

### Immediate (Weeks 1-2)
1. ✅ Complete architecture migration (DONE!)
2. Test all components
3. Migrate existing CSV data
4. Validate backtests match old results

### Short-term (Weeks 3-4)
1. Add more indicators (RSI, MACD, Bollinger Bands)
2. Develop additional strategies
3. Create strategy comparison tools
4. Build optimization pipeline

### Medium-term (Months 2-3)
1. Open Sinopac Securities account
2. Get Shioaji API access
3. Test with Shioaji simulation mode
4. Develop order management system
5. Add risk management controls

### Long-term (Months 4-6)
1. Paper trade for at least 1 month
2. Start live trading with small capital
3. Gradually scale up
4. Add portfolio management
5. Explore machine learning strategies

## Common Pitfalls to Avoid

### 1. **Over-optimization**
- Don't optimize on small datasets
- Use walk-forward analysis
- Test on out-of-sample data
- Beware of curve fitting

### 2. **Ignoring Transaction Costs**
- Taiwan costs: ~0.4-0.5% round-trip
- Can significantly impact profitability
- Test strategies with realistic costs

### 3. **Insufficient Testing**
- Backtest at least 2-3 years
- Test across different market conditions
- Include bear markets
- Validate on multiple symbols

### 4. **Poor Risk Management**
- Never risk more than 1-2% per trade
- Use stop losses
- Limit total exposure
- Have emergency procedures

### 5. **Technical Failures**
- Server downtime
- Network issues
- API rate limits
- Database corruption

Always have:
- Kill switch (emergency stop)
- Backup systems
- Alert mechanisms
- Recovery procedures

## Resources

### Taiwan Market
- Taiwan Stock Exchange: https://www.twse.com.tw/
- Securities & Futures Bureau: https://www.sfb.gov.tw/
- Taiwan Economic Journal: https://www.tej.com.tw/

### Technical
- Shioaji Documentation: https://sinotrade.github.io/
- FinMind (Taiwan data): https://finmindtrade.com/
- Backtesting.py: https://kernc.github.io/backtesting.py/

### Learning
- QuantStart: https://www.quantstart.com/
- Quantitative Trading: Books by Ernest Chan
- Taiwan traders community: PTT Stock board

## Support

For questions about Taiwan market specifics or system implementation:
1. Check existing documentation
2. Review code comments
3. Open an issue on the repository

---

**Final Advice**: Start small, test thoroughly, and never risk money you can't afford to lose. Automated trading is powerful but requires careful development, testing, and monitoring.

Good luck with your quantitative trading journey! 🚀
