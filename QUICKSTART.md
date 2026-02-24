# 🚀 Quick Start Guide

Your DinDin Quant Bot is ready to use! Follow these steps to get started.

## ✅ Migration Complete

- ✅ **426 rows** of historical data imported
- ✅ **2337.TW**: 248 trading days
- ✅ **6944.TW**: 178 trading days
- ✅ Old files archived in `archive/` folder
- ✅ Database ready at `data/database/market_data.db`

## 🎯 Quick Start (3 Steps)

### Step 1: Navigate to Project

```bash
cd /Users/dindin/Desktop/DinDin_Quant_Bot
```

### Step 2: Launch Dashboard

**Option A - Easy Way (Recommended):**
```bash
./run_dashboard.sh
```

**Option B - Manual Way:**
```bash
source quant_env/bin/activate
streamlit run src/presentation/dashboard/app.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Step 3: Explore!

In the dashboard you can:
- 🎯 **Select trading strategy** (MFI Hunter or RSI+MFI Consensus)
- 📊 View price charts with indicators
- 🎛️ Adjust strategy parameters with sliders
- 📈 See real-time backtest results
- 💡 Get AI trading recommendations
- 📉 Compare different parameter combinations

## 📚 Common Tasks

### Fetch Latest Data

```bash
# Get fresh data for your stocks
python scripts/fetch_historical_data.py 2337.TW 6944.TW --days 365
```

### Run Batch Backtests

```bash
# Test strategy on multiple symbols
python scripts/run_batch_backtest.py 2337.TW 6944.TW

# With parameter optimization
python scripts/run_batch_backtest.py 2337.TW 6944.TW --optimize
```

### Add New Stock

```bash
# Fetch data for new symbol
python scripts/fetch_historical_data.py 2330.TW --days 365
```

Then add it to the dashboard dropdown in `src/presentation/dashboard/components/controls.py`

## 🎓 Learning Path

### 1. **Understand the Architecture** (30 mins)
Read: `docs/ARCHITECTURE.md`
- Learn the 4-layer structure
- Understand data flow
- See how components connect

### 2. **Create Your First Strategy** (1 hour)
Read: `docs/STRATEGIES.md`
- Copy the MFI Hunter template
- Modify the logic
- Run backtest to see results

### 3. **Explore Taiwan Market Integration** (1 hour)
Read: `docs/TAIWAN_AUTOMATION_GUIDE.md`
- Learn about Shioaji API
- Understand Taiwan market specifics
- Plan for automation

## 🔧 Configuration

Edit `config/default.yaml` to change:
- Database path
- Default strategy parameters
- Logging level
- Initial capital for backtests

Environment-specific settings:
- `config/development.yaml` - Dev settings
- `config/production.yaml` - Production settings

## 📁 Project Structure

```
DinDin_Quant_Bot/
├── src/              # 💎 All source code
│   ├── core/         # Strategies, indicators, models
│   ├── infrastructure/  # Data providers, database
│   ├── application/  # Services, use cases
│   └── presentation/ # Dashboard UI
├── scripts/          # 🔧 Utility scripts
├── config/           # ⚙️ Configuration files
├── data/             # 💾 Database and data files
├── docs/             # 📚 Documentation
└── archive/          # 📦 Old files (safe to delete later)
```

## 🎨 Customization Ideas

### Easy Wins
1. **Add More Stocks**: Edit controls.py dropdown
2. **Tune Parameters**: Adjust MFI thresholds in sidebar
3. **Change Colors**: Modify chart colors in components/charts.py

### Medium Difficulty
1. **Add RSI Indicator**: Copy MFI structure, implement RSI
2. **Create New Strategy**: Combine MFI + RSI for consensus
3. **Add Email Alerts**: Integrate with SMTP for signal notifications

### Advanced
1. **Integrate Shioaji**: Connect to real-time Taiwan market data
2. **Machine Learning**: Train models on historical patterns
3. **Automated Trading**: Implement order execution with risk controls

## ⚠️ Important Notes

### Database Files
- `market_data.db` - Production database
- `market_data_dev.db` - Development database (used by default)

Both are identical now. The system uses `_dev` by default unless you set `ENVIRONMENT=production`.

### Archive Folder
The `archive/` folder contains all your old files as backup. You can:
- **Keep it**: Safe reference if you need to check old code
- **Delete it**: Once you've verified everything works

To delete:
```bash
rm -rf archive/
```

## 🐛 Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### Dashboard won't load
1. Check virtual environment is activated
2. Ensure database exists: `ls data/database/market_data.db`
3. Check for errors in terminal output

### No data showing
```bash
# Re-run migration
python scripts/migrate_old_data.py

# Or fetch fresh data
python scripts/fetch_historical_data.py 2337.TW 6944.TW
```

## 📞 Next Steps

1. ✅ **Test Dashboard** - Make sure everything displays correctly
2. ✅ **Read Documentation** - Understand the architecture
3. ✅ **Experiment** - Try different parameters
4. ✅ **Create Strategy** - Build your first custom strategy
5. ✅ **Plan Automation** - Read Taiwan automation guide

## 🎉 You're Ready!

Your quantitative trading system is production-ready with:
- ✅ Clean architecture
- ✅ Historical data imported
- ✅ Interactive dashboard
- ✅ Backtesting engine
- ✅ Extensible framework
- ✅ Comprehensive documentation

**Start exploring and happy trading! 📈💰**

---

For detailed documentation, see:
- `README.md` - Complete project overview
- `docs/ARCHITECTURE.md` - System design
- `docs/STRATEGIES.md` - Strategy development
- `docs/TAIWAN_AUTOMATION_GUIDE.md` - Full automation roadmap
