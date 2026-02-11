# ☁️ GitHub Actions Backup Setup

This is your **backup automation** that runs in parallel with your Mac's local cron job. If your Mac is off or has issues, GitHub Actions will still update your data.

---

## 🎯 How It Works

**Two Systems Running in Parallel:**

1. **Primary (Mac)**: Cron updates at 6 PM → saves to local database
2. **Backup (GitHub)**: Actions updates at 6 PM → saves to cloud artifact

**Benefits:**
- If Mac is off/sleeping, GitHub backup runs
- Both systems update independently
- Can download backup database if Mac fails
- Free (2,000 minutes/month - plenty for daily updates)

---

## 📋 Setup Steps (5 Minutes)

### **Step 1: Commit & Push to GitHub**

```bash
cd ~/Desktop/DinDin_Quant_Bot

# Add all new files
git add .

# Commit
git commit -m "Add GitHub Actions backup automation"

# Push to GitHub
git push origin main
```

### **Step 2: Add Secrets to GitHub**

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these 3 secrets:

| Name | Value | Where to find |
|------|-------|---------------|
| `SHIOAJI_API_KEY` | Your API key | From `.env` file |
| `SHIOAJI_SECRET_KEY` | Your secret key | From `.env` file |
| `SHIOAJI_PERSON_ID` | Your person ID | From `.env` file |

**Example:**
```
# In your .env file, you'll see:
SHIOAJI_API_KEY=abc123xyz
SHIOAJI_SECRET_KEY=def456uvw
SHIOAJI_PERSON_ID=A123456789

# Copy each value (without quotes) to GitHub secrets
```

### **Step 3: Enable GitHub Actions**

1. Go to your repo → **Actions** tab
2. If you see "Enable Actions", click it
3. You should see "Daily Stock Data Update (Backup)" workflow
4. Click on it

### **Step 4: Test It Manually**

1. In the workflow page, click **Run workflow** (right side)
2. Click the green **Run workflow** button
3. Wait ~2 minutes
4. Check if it succeeded ✅

---

## 🔍 Monitoring Your Backup

### **View Status:**
Go to: `https://github.com/YOUR_USERNAME/DinDin_Quant_Bot/actions`

You'll see:
- ✅ Green checkmark = Success
- ❌ Red X = Failed (check logs)
- 🟡 Yellow = Running

### **View Logs:**
1. Click on any workflow run
2. Click on the job name
3. Expand steps to see detailed logs

### **Download Backup Database:**
1. Go to workflow run
2. Scroll to **Artifacts** section
3. Download `market-database` (your full database)
4. Replace local database if needed

---

## 🚨 Disaster Recovery

**If your Mac database gets corrupted or lost:**

```bash
# 1. Download database from GitHub Actions
# Go to: https://github.com/YOUR_USERNAME/DinDin_Quant_Bot/actions
# Click latest successful run → Download "market-database" artifact

# 2. Extract the downloaded zip
unzip market-database.zip -d ~/Downloads/

# 3. Replace local database
cp ~/Downloads/market_data.db ~/Desktop/DinDin_Quant_Bot/data/database/

# 4. Verify
cd ~/Desktop/DinDin_Quant_Bot
source quant_env/bin/activate
sqlite3 data/database/market_data.db "SELECT COUNT(*) FROM daily_kline;"
```

---

## 📊 How the Parallel System Works

**Daily Flow:**

```
18:00 Taiwan Time
    ↓
┌───────────────────┬───────────────────┐
│   Mac (Primary)   │ GitHub (Backup)   │
├───────────────────┼───────────────────┤
│ Cron triggers     │ Actions triggers  │
│ Connects Shioaji  │ Connects Shioaji  │
│ Updates 93 stocks │ Updates 93 stocks │
│ Saves to local DB │ Saves to artifact │
│ Writes to log/    │ Creates summary   │
└───────────────────┴───────────────────┘
         ↓                     ↓
    Local DB              Cloud Artifact
    (Primary)             (Backup)
```

**If Mac is off:**
- GitHub Actions still runs ✅
- You can download the updated database later
- Or wait for next day when Mac is back on

**If GitHub is down (rare):**
- Mac still runs ✅
- Your local database stays updated

---

## 💰 Cost Analysis

**GitHub Free Tier:**
- 2,000 minutes/month free
- Each update: ~2 minutes
- Daily updates: 22 days × 2 min = 44 minutes/month
- **Usage: 2.2% of free quota** 🎉

**Artifact Storage:**
- Free up to 500MB
- Database: ~17MB
- Old artifacts auto-delete after 90 days
- **Storage: ~17MB (3.4% of quota)** 🎉

**Result:** Completely free! ✅

---

## ⚙️ Advanced Configuration

### **Change Update Time:**

Edit `.github/workflows/daily_update.yml`:

```yaml
schedule:
  # Run at 11:00 UTC (19:00 Taiwan time)
  - cron: '0 11 * * 1-5'
```

**Cron format:** `minute hour day month weekday`
- `0 10 * * 1-5` = 10:00 UTC, Mon-Fri (18:00 Taiwan)
- `30 11 * * 1-5` = 11:30 UTC, Mon-Fri (19:30 Taiwan)

### **Keep Artifacts Longer:**

```yaml
retention-days: 180  # Keep for 6 months instead of 90 days
```

### **Add Email Notifications:**

Go to GitHub → Settings → Notifications → Actions
- Enable "Send notifications for failed workflows"

---

## 🐛 Troubleshooting

### **Error: "Secrets not found"**
**Fix:** Add secrets to GitHub (Step 2)

### **Error: "No module named 'shioaji'"**
**Fix:** Make sure `requirements.txt` includes `shioaji>=1.0.0`

### **Error: "Database not found"**
**Fix:** This is normal for first run. It will create a new one.

### **Workflow doesn't run automatically**
**Fix:**
1. Check if Actions are enabled in repo settings
2. Make sure you pushed the `.github/workflows/` folder
3. Check the cron schedule is correct

### **"Download artifact" fails**
**Fix:** This is normal for first run (no previous artifact exists)

---

## 📈 Comparison: Mac vs GitHub

| Feature | Mac (Primary) | GitHub (Backup) |
|---------|---------------|-----------------|
| **Reliability** | 95% (if on) | 99.5% (always on) |
| **Speed** | Very fast | Moderate |
| **Cost** | $3/month electricity | Free |
| **Setup** | ✅ Done | ⏳ 5 minutes |
| **Access** | Local only | Worldwide |
| **Recovery** | Manual backup | Auto artifacts |

---

## ✅ Quick Start Checklist

- [ ] Run `sudo pmset -c sleep 0` to prevent Mac sleep
- [ ] `git add . && git commit -m "Add GitHub backup"`
- [ ] `git push origin main`
- [ ] Add 3 secrets to GitHub (API keys)
- [ ] Enable GitHub Actions
- [ ] Test workflow manually (Run workflow button)
- [ ] Check if it succeeds ✅
- [ ] Done! You now have dual backups

---

## 🎉 What You Get

After setup:
- ✅ Mac updates daily (primary)
- ✅ GitHub updates daily (backup)
- ✅ 90-day backup history in cloud
- ✅ Email alerts if failures
- ✅ Disaster recovery option
- ✅ Zero cost
- ✅ Peace of mind

---

**Next:** Just push your code to GitHub and add the secrets. The backup will run automatically!
