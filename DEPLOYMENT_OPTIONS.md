# 🌐 Deployment Options: Where to Run Your Bot

Your trading bot needs to run 24/7 to fetch daily data. Here are your options:

---

## 🖥️ **Option 1: Local Mac (Current Setup)**

### ✅ Pros:
- Free (already have the hardware)
- No setup needed (already working)
- Full control
- Fast development/testing

### ❌ Cons:
- **Must keep computer ON** (but can be locked)
- Mac can't sleep or shutdown
- Uses electricity (~$2-5/month)
- No remote access

### Setup:
**Already done!** Just prevent sleep:
```bash
# Prevent Mac sleep when plugged in
sudo pmset -c sleep 0

# Check current settings
pmset -g
```

### Best For:
- You usually leave Mac on anyway
- You're home most of the time
- Development/testing phase

---

## ☁️ **Option 2: Cloud VPS (Recommended for Production)**

### ✅ Pros:
- Always running (99.9% uptime)
- Mac can sleep/shutdown freely
- Access from anywhere
- Professional setup
- Fast, reliable

### ❌ Cons:
- Costs $5-10/month
- Requires basic Linux knowledge
- One-time setup (30 minutes)

### Recommended Providers:

| Provider | Cost | Specs |
|----------|------|-------|
| **DigitalOcean** | $6/month | 1GB RAM, 25GB SSD |
| **Linode** | $5/month | 1GB RAM, 25GB SSD |
| **Vultr** | $5/month | 1GB RAM, 25GB SSD |
| **AWS Lightsail** | $5/month | 1GB RAM, 40GB SSD |

### Quick Setup (DigitalOcean):
```bash
# 1. Create Ubuntu 22.04 droplet ($6/month)
# 2. SSH into server
ssh root@YOUR_SERVER_IP

# 3. Install dependencies
apt update && apt upgrade -y
apt install python3.10 python3-pip python3-venv git sqlite3 -y

# 4. Clone your project
cd /opt
git clone https://github.com/YOUR_USERNAME/DinDin_Quant_Bot.git
cd DinDin_Quant_Bot

# 5. Setup Python environment
python3 -m venv quant_env
source quant_env/bin/activate
pip install -r requirements.txt

# 6. Copy credentials
nano .env
# Paste your Shioaji credentials

# 7. Test it
python scripts/migrate_to_shioaji.py --update

# 8. Setup cron
crontab -e
# Add: 0 18 * * 1-5 cd /opt/DinDin_Quant_Bot && /opt/DinDin_Quant_Bot/quant_env/bin/python scripts/migrate_to_shioaji.py --update >> logs/daily_update.log 2>&1

# 9. (Optional) Setup Streamlit to run 24/7
sudo apt install screen -y
screen -S dashboard
cd /opt/DinDin_Quant_Bot
source quant_env/bin/activate
streamlit run src/presentation/dashboard/app.py --server.port 8501 --server.address 0.0.0.0
# Press Ctrl+A, then D to detach
# Access at: http://YOUR_SERVER_IP:8501
```

### Best For:
- Production use
- You want reliable 24/7 operation
- Mac needs to sleep/shutdown
- Remote access to dashboard

---

## 🆓 **Option 3: GitHub Actions (Free Tier)**

### ✅ Pros:
- **Completely free** (2,000 minutes/month)
- No server needed
- Mac can sleep/shutdown
- Version controlled
- Easy monitoring

### ❌ Cons:
- Requires GitHub repo
- Need cloud storage for database (Dropbox/S3/GCS)
- Slight complexity in setup
- 2,000 minute limit (enough for daily updates)

### Setup:

**Step 1: Push code to GitHub**
```bash
cd ~/Desktop/DinDin_Quant_Bot
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/DinDin_Quant_Bot.git
git push -u origin main
```

**Step 2: Add secrets to GitHub**
1. Go to your repo → Settings → Secrets and variables → Actions
2. Add secrets:
   - `SHIOAJI_API_KEY`
   - `SHIOAJI_SECRET_KEY`
   - `SHIOAJI_PERSON_ID`

**Step 3: Setup database storage**

Choose one:

**Option A: Dropbox (Easiest)**
```bash
pip install dropbox
# Get access token from https://www.dropbox.com/developers/apps
# Use Dropbox API to sync database
```

**Option B: AWS S3 (Cheapest)**
```bash
# Free tier: 5GB storage, 20K GET requests/month
aws s3 cp data/database/market_data.db s3://your-bucket/
```

**Option C: Google Drive**
```bash
pip install PyDrive2
# Use Google Drive API to sync database
```

**Step 4: Enable workflow**
- Workflow is already created (`.github/workflows/daily_update.yml`)
- Push to GitHub
- Go to Actions tab → Enable workflows
- Done! Runs daily at 6 PM Taiwan time

### Best For:
- You want free hosting
- Mac needs to sleep/shutdown often
- You're comfortable with Git/GitHub
- Don't mind slight complexity

---

## 🍓 **Option 4: Raspberry Pi (One-Time Cost)**

### ✅ Pros:
- One-time cost ($50-100)
- Tiny power consumption (~$1/year electricity)
- Runs 24/7 silently
- No monthly fees
- Learn IoT/embedded systems

### ❌ Cons:
- Upfront cost
- Basic setup required
- Slower than Mac/VPS
- Need monitor/keyboard for setup

### Setup:
```bash
# 1. Buy Raspberry Pi 4 (4GB RAM) + SD card
# 2. Install Raspberry Pi OS
# 3. Follow same steps as "Cloud VPS" setup
# 4. Leave it running 24/7
```

### Best For:
- Tech enthusiasts
- Want to learn embedded systems
- Prefer one-time cost vs monthly fee
- Have space for tiny computer

---

## 🎯 **Recommendation by Use Case:**

| Your Situation | Best Option | Why |
|----------------|-------------|-----|
| **Mac always on anyway** | Local Mac | Free, already working |
| **Mac sleeps often** | Cloud VPS | Reliable, professional |
| **Budget conscious** | GitHub Actions | Free, no hardware |
| **Learning/experimenting** | Raspberry Pi | Fun, educational |
| **Production trading** | Cloud VPS | 99.9% uptime, scalable |

---

## 📊 **Cost Comparison (Annual)**

| Option | Setup Time | Upfront | Monthly | Annual | Reliability |
|--------|------------|---------|---------|--------|-------------|
| Local Mac | 0 min | $0 | $3 | $36 | 95% |
| Cloud VPS | 30 min | $0 | $6 | $72 | 99.9% |
| GitHub Actions | 60 min | $0 | $0 | $0 | 99.5% |
| Raspberry Pi | 45 min | $75 | $0.10 | $1 | 98% |

---

## 🚀 **My Recommendation:**

### **Phase 1 (Now - Next Month): Local Mac**
- Keep current setup
- Test strategies
- Validate system
- **Cost: Free**

### **Phase 2 (When ready for production): Cloud VPS**
- Move to DigitalOcean/Linode
- 24/7 reliable operation
- Remote dashboard access
- **Cost: $6/month**

### **Phase 3 (Scaling up): Multi-region Cloud**
- Add redundancy
- Real-time trading
- Production database (PostgreSQL)
- **Cost: $20-50/month**

---

## ❓ **FAQ**

**Q: Can I use my Mac AND cloud server?**
A: Yes! Develop locally, deploy to cloud for 24/7 operation.

**Q: What if cloud server goes down?**
A: Rare (99.9% uptime). You'll get email alert, and it auto-restarts.

**Q: Can I move between options later?**
A: Yes! The code is portable. Just copy files and setup cron.

**Q: Do I need all this for backtesting?**
A: No! Backtesting works fine on local Mac. This is only for daily data updates.

---

**Current Status:** ✅ Local Mac automation is working. You can decide later if you want to move to cloud.
