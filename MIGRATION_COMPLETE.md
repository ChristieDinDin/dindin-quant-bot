# 🎉 Shioaji Setup Complete!

## ✅ What's Done:

1. ✅ **Shioaji installed** (v1.3.2)
2. ✅ **Credentials configured** in `.env`
3. ✅ **Connection tested** - Working perfectly!
4. ✅ **Migration script created** - Ready to use

---

## 🚀 How to Use Your New System

### Option 1: Bulk Import Historical Data (yfinance)
**Use this FIRST to get all historical data:**

```bash
cd /Users/dindin/Desktop/DinDin_Quant_Bot
source quant_env/bin/activate

# Import your current stocks (5 years of data)
python scripts/migrate_to_shioaji.py --stocks 6944.TW 2337.TW 2330.TW

# Or import top 50 Taiwan stocks
python scripts/migrate_to_shioaji.py --all-taiwan

# Or custom time range
python scripts/migrate_to_shioaji.py --stocks 2330.TW --years 10
```

**This uses yfinance (free, unlimited) for bulk historical data.**

---

### Option 2: Daily Update (Shioaji)
**Use this DAILY to keep data fresh:**

```bash
# Update all your stocks with yesterday's data
python scripts/migrate_to_shioaji.py --update --stocks 6944.TW 2337.TW 2330.TW

# Or update all top stocks
python scripts/migrate_to_shioaji.py --update --all-taiwan
```

**This uses Shioaji (1 API call per stock) - very rate-limit friendly!**

---

### Option 3: Automate Daily Updates (Recommended)
**Set up a cron job to run automatically every day:**

```bash
# Edit crontab
crontab -e

# Add this line (runs every weekday at 6 PM):
0 18 * * 1-5 cd /Users/dindin/Desktop/DinDin_Quant_Bot && source quant_env/bin/activate && python scripts/migrate_to_shioaji.py --update --all-taiwan
```

---

## 📊 Data Flow (Your New System)

```
┌─────────────────────────────────────┐
│ HISTORICAL DATA (One-time)          │
│ yfinance → Database                 │
│ • Free, unlimited                   │
│ • 2020-2025 bulk import            │
│ • ~500 MB for 1,700 stocks         │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ DATABASE (market_data.db)           │
│ • All your stock data               │
│ • Local, fast access                │
│ • Timezone-naive (clean!)           │
└─────────────────────────────────────┘
                 ▲
                 │
┌─────────────────────────────────────┐
│ DAILY UPDATES (Automated)           │
│ Shioaji → Database                  │
│ • 1 API call/stock/day              │
│ • Only fetches new data             │
│ • Rate-limit friendly               │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ YOUR STRATEGIES & DASHBOARD         │
│ • MFI Hunter                        │
│ • RSI+MFI Consensus                 │
│ • Backtesting                       │
│ • Real-time monitoring              │
└─────────────────────────────────────┘
```

---

## 💡 Smart Usage Strategy

### Week 1: Setup Historical Data
```bash
# Day 1: Import your watchlist (fast)
python scripts/migrate_to_shioaji.py --stocks 6944.TW 2337.TW 2330.TW

# Day 2-3: Expand to top 50 stocks
python scripts/migrate_to_shioaji.py --all-taiwan
```

### Week 2+: Daily Updates
```bash
# Every trading day (automated):
python scripts/migrate_to_shioaji.py --update --all-taiwan
```

### Monthly: Backfill if Needed
```bash
# If you missed some days:
python scripts/migrate_to_shioaji.py --stocks 2330.TW --years 1
```

---

## 📈 Rate Limit Usage

### Your Current Limits:
- **yfinance**: Unlimited (use for historical)
- **Shioaji**: ~300 requests/hour (use for daily updates)

### Daily Update Cost:
```
50 stocks × 1 request each = 50 API calls/day
= 16% of your hourly limit
= Very safe! ✅
```

### If You Want to Monitor 1,700 Stocks:
```
1,700 stocks × 1 request = 1,700 API calls/day
Split into 6 batches of ~280 stocks each
Run every hour during trading session
= Still within limits! ✅
```

---

## 🎯 What Happens Now?

1. **Your Dashboard** (`./run_dashboard.sh`) automatically uses the database
2. **No code changes needed** - it just works!
3. **Data stays fresh** with daily Shioaji updates
4. **Rate limits protected** - migration script has built-in delays

---

## 🔧 Maintenance

### Check Database Size:
```bash
du -sh data/database/market_data.db
# Should show: ~100-500 MB for normal usage
```

### Check Last Update:
```bash
sqlite3 data/database/market_data.db "SELECT symbol, MAX(date) as last_date FROM daily_kline GROUP BY symbol ORDER BY last_date DESC LIMIT 10;"
```

### Backup Database:
```bash
cp data/database/market_data.db data/database/backup_$(date +%Y%m%d).db
```

---

## 🚨 Troubleshooting

### "Shioaji connection failed"
- Check .env credentials are correct
- Keep `SHIOAJI_SIMULATION=true` for testing
- Script will fallback to yfinance automatically

### "Rate limit exceeded"
- Wait 1 hour for quota reset
- Use `--stocks` with fewer symbols
- Spread updates across multiple hours

### "No data returned"
- Might be weekend/holiday
- Check stock is still listed
- Try a different symbol (2330.TW always works)

---

## 📝 Recommended Workflow

**Daily (Automated):**
```bash
# Morning: Update database
python scripts/migrate_to_shioaji.py --update --all-taiwan

# Anytime: Use dashboard
./run_dashboard.sh
```

**Weekly:**
- Review database size
- Check for failed updates
- Backup database

**Monthly:**
- Backfill any gaps
- Add new stocks to watchlist
- Review rate limit usage

---

## 🎉 You're All Set!

Your quant trading system is now production-ready:
- ✅ Historical data from yfinance
- ✅ Daily updates from Shioaji
- ✅ Local database for fast access
- ✅ Rate-limit protected
- ✅ Timezone issues solved
- ✅ Dashboard fully functional

**Start with:**
```bash
# 1. Import your stocks
python scripts/migrate_to_shioaji.py --stocks 6944.TW 2337.TW

# 2. Launch dashboard
./run_dashboard.sh

# 3. Test your strategies!
```

**Happy trading! 🚀📈**
