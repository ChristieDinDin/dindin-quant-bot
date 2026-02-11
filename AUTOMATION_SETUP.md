# 🤖 Daily Stock Data Automation

## ✅ What's Set Up

Your system is now configured to **automatically fetch the latest Taiwan stock data** every weekday at **6:00 PM** (after Taiwan market closes at 1:30 PM).

### Automation Details

- **Schedule**: Monday-Friday, 6:00 PM (18:00)
- **Stocks Updated**: All 93 stocks in your database
- **Data Source**: Shioaji API (simulation mode - safe)
- **Method**: Incremental updates (only fetches missing dates)
- **Logging**: Automatic logs saved to `logs/daily_update_YYYYMMDD.log`

## 📋 Files Created

1. **`scripts/daily_update.sh`**
   - Shell script that runs the daily update
   - Handles virtual environment activation
   - Logs all output
   - Auto-cleans old logs (keeps last 30 days)

2. **Cron Job**
   - Automatically runs `daily_update.sh` every weekday at 6 PM
   - No manual intervention needed

## 🔍 How to Monitor

### Check if it's running:
```bash
crontab -l
# Should show: 0 18 * * 1-5 /Users/dindin/Desktop/DinDin_Quant_Bot/scripts/daily_update.sh
```

### View today's log:
```bash
cat ~/Desktop/DinDin_Quant_Bot/logs/daily_update_$(date +%Y%m%d).log
```

### View all logs:
```bash
ls -lh ~/Desktop/DinDin_Quant_Bot/logs/
```

### Test manually (without waiting for 6 PM):
```bash
cd ~/Desktop/DinDin_Quant_Bot
source quant_env/bin/activate
python scripts/migrate_to_shioaji.py --update
```

## 📊 What Happens Each Day

1. **18:00** - Cron triggers the update script
2. Script activates your Python environment
3. Connects to Shioaji API (simulation mode)
4. Checks all 93 stocks for new data since last update
5. Fetches and saves any new trading days
6. Logs results to `logs/daily_update_YYYYMMDD.log`
7. Your dashboard automatically shows the latest data

## 🛠️ Troubleshooting

### If updates stop working:

**Check cron is running:**
```bash
crontab -l
```

**Check recent logs:**
```bash
tail -50 ~/Desktop/DinDin_Quant_Bot/logs/daily_update_*.log
```

**Manually test the script:**
```bash
/Users/dindin/Desktop/DinDin_Quant_Bot/scripts/daily_update.sh
```

**Re-install the cron job:**
```bash
echo "0 18 * * 1-5 /Users/dindin/Desktop/DinDin_Quant_Bot/scripts/daily_update.sh" | crontab -
```

### Common Issues

1. **"No data for today"**
   - Normal! Market hasn't closed yet or it's a holiday
   - Script will check again tomorrow

2. **"Already up-to-date"**
   - Good! Data is current, no action needed

3. **"Failed to connect to Shioaji"**
   - Check your `.env` file has correct credentials
   - Check internet connection
   - Verify Shioaji API is operational

## 🔧 Customization

### Change the update time:
```bash
# Edit the cron job (format: minute hour day month weekday)
crontab -e
# Example: Change to 7 PM (19:00):
# 0 19 * * 1-5 /Users/dindin/Desktop/DinDin_Quant_Bot/scripts/daily_update.sh
```

### Update specific stocks only:
```bash
# Edit scripts/migrate_to_shioaji.py
# Change the symbols list in the --update section
```

### Disable automation:
```bash
crontab -r  # Remove all cron jobs (be careful!)
# Or edit and remove just this line:
crontab -e
```

## 📈 Performance

- **Update time**: ~30 seconds for 93 stocks
- **Data usage**: ~1-2 MB per update
- **Storage**: ~10 KB per stock per day (compressed)
- **Rate limits**: 60 requests/minute (Shioaji)

## 🎯 Next Steps

1. ✅ **You're done!** - Updates happen automatically
2. 🔍 Check tomorrow's log to verify it worked
3. 📊 Your dashboard will always show the latest data
4. 🚀 Focus on developing strategies, not data management

---

**Pro Tip**: If you want to force an update right now (instead of waiting for 6 PM), just run:
```bash
cd ~/Desktop/DinDin_Quant_Bot && source quant_env/bin/activate && python scripts/migrate_to_shioaji.py --update
```

This is especially useful for TSMC - run it tomorrow to retry fetching its full historical data!
